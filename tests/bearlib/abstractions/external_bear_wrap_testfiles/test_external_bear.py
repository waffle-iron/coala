import sys
import json

if __name__ == "__main__":

    line = sys.stdin.read()
    args = json.loads(line)

    out = [

        {
            'message': "This is wrong",
            'file': args['filename'],
            'severity': "MAJOR",
            'line': 1
        }, {
            'message': "This is wrong too",
            'file': args['filename'],
            'severity': "INFO",
            'line': 3
        }

    ]

    json_dump = json.dumps(out)
    sys.stdout.write(json_dump)
