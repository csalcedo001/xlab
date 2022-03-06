from subprocess import Popen, PIPE, STDOUT
from argparse import Namespace
import copy
import json
import sys
import os
import traceback
import fasteners

from . import cache
from .utils import merge_dicts, substract_dict_keys

def setup(*args, **kwargs):
    return Setup(*args, **kwargs)

class Setup:
    def __init__(self, parser, hash_ignore=[]):
        parser.add_argument("--exp-config", default='{}', type=json.loads)
        parser.add_argument("--exp-dir", default=False, action="store_const", const=True)
        parser.add_argument("--exp-is-complete", default=False, action="store_const", const=True)
        parser.add_argument("--exp-force", default=False, action="store_const", const=True)
        parser.add_argument("--exp-no-wait", default=False, action="store_const", const=True)
        parser.add_argument("--exp-hash", default=False, action="store_const", const=True)

        self.parser = parser

        self._hash_ignore = hash_ignore

        self._run_lock = None
    
    def __enter__(self):
        default_args_keys = ['exp_config', 'exp_dir', 'exp_is_complete', 'exp_force', 'exp_no_wait', 'exp_hash']
        default_config_keys = ['executable']

        args = {
            'executable': sys.argv[0]
        }
        args = merge_dicts(args, dict(vars(self.parser.parse_args())))
        args = merge_dicts(args, args['exp_config'])

        self._all_args = args

        user_args = substract_dict_keys(args, default_args_keys + default_config_keys)
        config_args = substract_dict_keys(args, default_args_keys)
        hash_args = substract_dict_keys(args, 
            [k for k in default_config_keys if k not in ['executable']] +
            default_args_keys + self._hash_ignore
        )
        
        self.args = Namespace(**user_args)
        

        exists = cache.exists(hash_args)
        self.dir = cache.get_dir(hash_args) if exists else cache.assign_dir(hash_args)

        os.makedirs(self.dir, exist_ok=True)

        path = os.path.join(self.dir, 'config.json')
        if not os.path.exists(path) or args['exp_force']:
            with open(path, 'w') as out_file:
                json.dump(config_args, out_file, indent=4)

        if args['exp_hash']:
            print(cache.get_hash(hash_args))
            exit(0)

        if args['exp_dir']:
            print(self.dir)
            exit(0)
        
        if args['exp_is_complete']:
            print(cache.is_complete(hash_args))
            exit(0)

        self._run_lock = fasteners.InterProcessLock(os.path.join(self.dir, '.run.lock'))
        self._run_lock.acquire()
        
        if cache.is_complete(hash_args) and not args['exp_force']:
            print('*** Using cached data on {}'.format(self.dir))
            self._run_lock.release()
            exit(0)
        
        return self
    
    
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            self._run_lock.release()
            return False

        default_args_keys = ['exp_config', 'exp_dir', 'exp_is_complete', 'exp_force', 'exp_no_wait', 'exp_hash']
        default_config_keys = ['executable']
        
        hash_args = substract_dict_keys(self._all_args, 
            [k for k in default_config_keys if k not in ['executable']] +
            default_args_keys + self._hash_ignore
        )

        cache.set_complete(hash_args)

        self._run_lock.release()

        return True



class Experiment:
    def __init__(self, executable, req_args, command):
        self.executable = executable
        self.command = command
        self.args = req_args
        
        self._last_full_hash = None
        self._last_local_hash = cache.get_hash(self.args)

        dir = self.get_dir()
        
        path = os.path.join(dir, 'config.json')
        with open(path, 'r') as in_file:
            self.args = json.load(in_file)

    def run(self, special_command=None, use_cached=True, wait=True):
        tmp_args = {
            'executable': self.executable
        }
        tmp_args = merge_dicts(tmp_args, self.args)

        command = special_command if special_command != None else self.command
        command = command.format(**tmp_args)
        command_parts = command.split(' ')
        if not use_cached:
            command_parts.append('--exp-force')
        if not wait:
            command_parts.append('--exp-no-wait')
        command_parts += ["--exp-config", "{}".format(json.dumps(self.args))]
        
        exe = Popen(command_parts)
        exe.communicate()
        # TODO: catch errors

    def get_hash(self):
        curr_local_hash = cache.get_hash(self.args)
        if curr_local_hash == self._last_local_hash and self._last_full_hash is not None:
            return self._last_full_hash
        self._last_local_hash = curr_local_hash

        tmp_args = {
            'executable': self.executable
        }
        tmp_args = merge_dicts(tmp_args, self.args)

        command = self.command.format(**tmp_args)
        command_parts = command.split(' ')
        command_parts.append("--exp-hash")
        command_parts += ["--exp-config", "{}".format(json.dumps(self.args))]

        exe = Popen(command_parts, stdout=PIPE, stderr=PIPE)
        out, err = exe.communicate()

        lines = out.decode(sys.stdin.encoding).split('\n')
        err_msg = err.decode(sys.stdin.encoding)

        if len(lines) < 2:
            if len(err) > 0:
                raise Exception(err_msg)
            else:
                raise Exception("error: Command did not print an output.")

        hash = lines[-2]

        if not cache.exists(hash):
            if len(err) > 0:
                raise Exception(err_msg)
            else:
                raise Exception("error: Command returned invalid hash.")

        self._last_full_hash = hash

        return hash

    def get_dir(self):
        return cache.get_dir(self.get_hash())

    def is_complete(self):
        return cache.is_complete(self.get_hash())