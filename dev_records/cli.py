"""Machine-readable CLI."""
import argparse
import json
import os
import sys
from .core import Store


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parser():
    p = Parser(prog='dev-records')
    p.add_argument('--store', default=os.environ.get('DEV_RECORDS_STORE'))
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('status')
    project = sub.add_parser('project').add_subparsers(dest='action', required=True).add_parser('add')
    project.add_argument('--id', required=True)
    project.add_argument('--source', required=True)
    project.add_argument('--name')
    task = sub.add_parser('task').add_subparsers(dest='action', required=True).add_parser('start')
    task.add_argument('--project', required=True)
    task.add_argument('--title', required=True)
    task.add_argument('--id')
    run = sub.add_parser('run')
    run.add_argument('--project', required=True)
    run.add_argument('--task', required=True)
    run.add_argument('--cwd')
    run.add_argument('--timeout', type=float)
    run.add_argument('argv', nargs=argparse.REMAINDER)
    return p


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if not args.store:
            raise ValueError('--store or DEV_RECORDS_STORE is required')
        store = Store(args.store)
        code = 0
        if args.command == 'init':
            result = store.init()
        elif args.command == 'status':
            result = store.status()
        elif args.command == 'project':
            result = store.add_project(args.id, args.source, args.name)
        elif args.command == 'task':
            result = store.start_task(args.project, args.title, args.id)
        else:
            if not args.argv or args.argv[0] != '--':
                raise ValueError('use -- before program and arguments')
            result, code = store.run(args.project, args.task, args.argv[1:], args.cwd, args.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return code
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
