import json
from functools import partial
from collections import OrderedDict

from coalib.bears.LocalBear import LocalBear
from coala_decorators.decorators import enforce_signature
from coalib.misc.Shell import run_shell_command
from coalib.results.Diff import Diff
from coalib.results.Result import Result
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.settings.FunctionMetadata import FunctionMetadata


def _prepare_options(options):
    """
    Prepares options for a given options dict in-place.

    :param options: The options dict that contains user/developer inputs.
    :raises ValueError: Raised when illegal options are specified.
    """
    allowed_options = {"executable",
                       "settings"}

    # Check for illegal superfluous options.
    superfluous_options = options.keys() - allowed_options
    if superfluous_options:
        raise ValueError(
            "Invalid keyword arguments provided: " +
            ", ".join(repr(s) for s in sorted(superfluous_options)))


def _create_wrapper(klass, options):
    class ExternalBearWrapBase(LocalBear):

        @staticmethod
        def create_arguments():
            """
            This method has to be implemented by the class that uses
            the decorator in order to create the arguments needed for
            the executable.
            """
            raise NotImplementedError

        @classmethod
        def get_executable(cls):
            """
            Returns the executable of this class.

            :return: The executable name.
            """
            return options["executable"]

        @staticmethod
        def normalize_desc(val):
            """
            Normalizes the description of the parameters only if there
            is none provided.

            :return: A value for the OrderedDict in the FunctionMetada object.
            """
            if val[0] != "":
                return val
            desc = "No description given."
            if len(val) == 2:
                return (desc, val[1])
            else:
                desc += " Defaults to " + str(val[2])
                return (desc, val[1], val[2])

        @classmethod
        def get_non_optional_params(cls):
            """
            Fetches the non_optional_params from ``options['settings']``
            and also normalizes their descriptions.

            :return: An OrderedDict that is used to create a
                FunctionMetada object.
            """
            non_optional_params = {}
            for key, value in options['settings'].items():
                if len(value) == 2:
                    non_optional_params[key] = cls.normalize_desc(value)
            return OrderedDict(non_optional_params)

        @classmethod
        def get_optional_params(cls):
            """
            Fetches the optional_params from ``options['settings']``
            and also normalizes their descriptions.

            :return: An OrderedDict that is used to create a
                FunctionMetada object.
            """
            optional_params = {}
            for key, value in options['settings'].items():
                if len(value) == 3:
                    optional_params[key] = cls.normalize_desc(value)
            return OrderedDict(optional_params)

        @classmethod
        def get_metadata(cls):
            return FunctionMetadata(
                'run',
                optional_params=cls.get_optional_params(),
                non_optional_params=cls.get_non_optional_params())

        @staticmethod
        def get_severity(result):
            """
            Returns the severity corresponding to the one from the
                parsed JSON

            :param result: A result dict extracted from the parsed JSON

            :return: A RESULT_SEVERITY
            """
            if not 'severity' in result or result['severity'] == "NORMAL":
                return RESULT_SEVERITY.NORMAL
            elif result['severity'] == "MAJOR":
                return RESULT_SEVERITY.MAJOR
            elif result['severity'] == "INFO":
                return RESULT_SEVERITY.INFO
            else:
                raise ValueError

        def parse_output(self, out, filename):
            """
            Parses the output JSON into Result objects

            :param out: Raw output from the given executable (should be JSON)
            :param filename: The filename of the analyzed file. Needed to
                create the Result objects.

            :return: The Result objects.
            """
            output = json.loads(out)

            for result in output:
                yield Result.from_values(
                    origin=self,
                    message=result['message'],
                    file=filename,
                    line=result['line'],
                    severity=self.get_severity(result))

        def run(self, filename, file, **kwargs):
            json_string = json.dumps({'filename': filename,
                                      'file': file})

            args = self.create_arguments()
            try:
                args = tuple(args)
            except TypeError:
                self.err("The given arguments "
                         "{!r} are not iterable.".format(args))
                return

            shell_command = (self.get_executable(),) + args
            out, err = run_shell_command(shell_command, json_string)

            return self.parse_output(out, filename)

    result_klass = type(klass.__name__, (klass, ExternalBearWrapBase), {})
    result_klass.__doc__ = klass.__doc__ if klass.__doc__ else ""
    return result_klass


@enforce_signature
def external_bear_wrap(executable: str, **options):

    options["executable"] = executable
    _prepare_options(options)

    return partial(_create_wrapper, options=options)
