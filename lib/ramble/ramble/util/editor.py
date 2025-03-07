# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Module for finding the user's preferred text editor.

Defines one function, editor(), which invokes the editor defined by the
user's VISUAL environment variable if set. We fall back to the editor
defined by the EDITOR environment variable if VISUAL is not set or the
specified editor fails (e.g. no DISPLAY for a graphical editor). If
neither variable is set, we fall back to one of several common editors,
raising an EnvironmentError if we are unable to find one.
"""
import os
import shlex

import ramble.config
from ramble.util.logger import logger
from spack.util.executable import which_string


#: editors to try if VISUAL and EDITOR are not set
_default_editors = ["vim", "vi", "emacs", "nano"]


def _find_exe_from_env_var(var):
    """Find an executable from an environment variable.

    Args:
        var (str): environment variable name

    Returns:
        (str or None, list): executable string (or None if not found) and
            arguments parsed from the env var
    """
    # try to get the environment variable
    exe = os.environ.get(var)
    if not exe:
        return None, []

    # split env var into executable and args if needed
    args = shlex.split(str(exe))
    if not args:
        return None, []

    exe = which_string(args[0])
    args = [exe] + args[1:]
    return exe, args


def editor(*args, **kwargs):
    """Invoke the user's editor.

    This will try to execute the following, in order:

      1. $VISUAL <args>    # the "visual" editor (per POSIX)
      2. $EDITOR <args>    # the regular editor (per POSIX)
      3. some default editor (see ``_default_editors``) with <args>

    If an environment variable isn't defined, it is skipped.  If it
    points to something that can't be executed, we'll print a
    warning. And if we can't find anything that can be executed after
    searching the full list above, we'll raise an error.

    Arguments:
        args (list of str): args to pass to editor

    Optional Arguments:
        _exec_func (function): invoke this function instead of ``os.execv()``

    """
    # allow this to be customized for testing
    _exec_func = kwargs.get("_exec_func", os.execv)

    def try_exec(exe, args, var=None):
        """Try to execute an editor with execv, and warn if it fails.

        Returns: (bool) False if the editor failed, ideally does not
            return if ``execv`` succeeds, and ``True`` if the
            ``_exec_func`` does return successfully.
        """
        try:
            _exec_func(exe, args)
            return True

        except OSError as e:
            if ramble.config.get("config:debug"):
                raise

            # Show variable we were trying to use, if it's from one
            if var:
                exe = f"${var} ({exe})"
            logger.warn(f"Could not execute {exe} due to error: {e}")
            return False

    def try_env_var(var):
        """Find an editor from an environment variable and try to exec it.

        This will warn if the variable points to something is not
        executable, or if there is an error when trying to exec it.
        """
        if var not in os.environ:
            return False

        exe, editor_args = _find_exe_from_env_var(var)
        if not exe:
            logger.warn(f"${var} is not an executable: {os.environ[var]}")
            return False

        full_args = editor_args + list(args)
        return try_exec(exe, full_args, var)

    # try standard environment variables
    if try_env_var("VISUAL"):
        return
    if try_env_var("EDITOR"):
        return

    # nothing worked -- try the first default we can find don't bother
    # trying them all -- if we get here and one fails, something is
    # probably much more deeply wrong with the environment.
    exe = which_string(*_default_editors)
    if try_exec(exe, [exe] + list(args)):
        return

    # Fail if nothing could be found
    raise OSError(
        "No text editor found! Please set the VISUAL and/or EDITOR "
        "environment variable(s) to your preferred text editor."
    )
