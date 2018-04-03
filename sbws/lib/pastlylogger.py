from datetime import datetime
from threading import Lock, current_thread


class PastlyLogger:
    """
    PastlyLogger - logging class inspired by Tor's logging API

    error, warn, etc. are file names to open for logging.
    If a log level doesn't have a file name given for it, messages destined
    for that level cascade down to the next noisiest level.
    Example 1: warn=foo.txt, debug=bar.txt
      error and warn messages go to foo.txt, all other messages to bar.txt
    Example 2: notice=baz.txt
      error, warn, and notice messages go to baz.txt, all others are lost

    overwrite is a list of log levels that should overwrite their log file
    when opening instead of appending.
    Example: notice=a.txt, info=b.txt, overwrite=['info']
      error, warn, and notice messages are appended to a.txt;
      b.txt is overwritten and info messages are appended to it;
      all debug messages are lost

    log_threads tells the logger whether or not to log thread names

    log_levels tells the logger whether or not to log the level (notice, info,
    warn, etc.)

    log_date tells the logger whether or not to log the date

    default tells the logger what level to log at when called with
    log('foobar') instead of log.info('foobar')
    """
    def __init__(self, error=None, warn=None, notice=None, info=None,
                 debug=None, overwrite=[], log_threads=False, default='notice',
                 log_levels=True, log_date=True):

        self.log_threads = log_threads
        self.log_levels = log_levels
        self.log_date = log_date
        assert default in ['debug', 'info', 'notice', 'warn', 'error']
        self.default_level = default

        # buffering=1 means line-based buffering
        if error:
            self.error_fd = open(error, 'w' if 'error' in overwrite else 'a',
                                 buffering=1)
            self.error_fd_mutex = Lock()
        else:
            self.error_fd = None
            self.error_fd_mutex = None
        if warn:
            self.warn_fd = open(warn, 'w' if 'warn' in overwrite else 'a',
                                buffering=1)
            self.warn_fd_mutex = Lock()
        else:
            self.warn_fd = None
            self.warn_fd_mutex = None
        if notice:
            self.notice_fd = open(notice, 'w' if 'notice' in overwrite else
                                  'a', buffering=1)
            self.notice_fd_mutex = Lock()
        else:
            self.notice_fd = None
            self.notice_fd_mutex = None
        if info:
            self.info_fd = open(info, 'w' if 'info' in overwrite else 'a',
                                buffering=1)
            self.info_fd_mutex = Lock()
        else:
            self.info_fd = None
            self.info_fd_mutex = None
        if debug:
            self.debug_fd = open(debug, 'w' if 'debug' in overwrite else 'a',
                                 buffering=1)
            self.debug_fd_mutex = Lock()
        else:
            self.debug_fd = None
            self.debug_fd_mutex = None

        # self.debug('Creating PastlyLogger instance')

    def __call__(self, *s):
        if self.default_level == 'debug': return self.debug(*s)
        elif self.default_level == 'info': return self.info(*s)
        elif self.default_level == 'notice': return self.notice(*s)
        elif self.default_level == 'warn': return self.warn(*s)
        elif self.default_level == 'error': return self.error(*s)

    def __del__(self):
        # self.debug('Deleting PastlyLogger instance')
        self.flush()
        if self.error_fd: self.error_fd.close()
        if self.warn_fd: self.warn_fd.close()
        if self.notice_fd: self.notice_fd.close()
        if self.info_fd: self.info_fd.close()
        if self.debug_fd: self.debug_fd.close()
        self.error_fd, self.warn_fd = None, None
        self.notice_fd, self.info_fd, self.debug_fd = None, None, None
        if self.error_fd_mutex:
            if not self.error_fd_mutex.acquire(blocking=False):
                self.error_fd_mutex.release()
        if self.warn_fd_mutex:
            if not self.warn_fd_mutex.acquire(blocking=False):
                self.warn_fd_mutex.release()
        if self.notice_fd_mutex:
            if not self.notice_fd_mutex.acquire(blocking=False):
                self.notice_fd_mutex.release()
        if self.info_fd_mutex:
            if not self.info_fd_mutex.acquire(blocking=False):
                self.info_fd_mutex.release()
        if self.debug_fd_mutex:
            if not self.debug_fd_mutex.acquire(blocking=False):
                self.debug_fd_mutex.release()

    def _log_file(fd, lock, log_levels, log_threads, log_date, level, *s):
        assert fd
        prefix = []
        if log_date: prefix.append('[{}]'.format(datetime.now()))
        if log_levels: prefix.append('[{}]'.format(level))
        if log_threads: prefix.append('[{}]'.format(current_thread().name))
        prefix = ' '.join(prefix)
        s = ' '.join([str(s_) for s_ in s])
        if prefix: s = ' '.join([prefix, s])
        lock.acquire()
        fd.write('{}\n'.format(s))
        lock.release()

    def flush(self):
        if self.error_fd: self.error_fd.flush()
        if self.warn_fd: self.warn_fd.flush()
        if self.notice_fd: self.notice_fd.flush()
        if self.info_fd: self.info_fd.flush()
        if self.debug_fd: self.debug_fd.flush()

    def debug(self, *s, level='debug'):
        if self.debug_fd: return PastlyLogger._log_file(
                self.debug_fd, self.debug_fd_mutex, self.log_levels,
                self.log_threads, self.log_date, level, *s)
        return None

    def info(self, *s, level='info'):
        if self.info_fd: return PastlyLogger._log_file(
                self.info_fd, self.info_fd_mutex, self.log_levels,
                self.log_threads, self.log_date, level, *s)
        else: return self.debug(*s, level=level)

    def notice(self, *s, level='notice'):
        if self.notice_fd: return PastlyLogger._log_file(
                self.notice_fd, self.notice_fd_mutex, self.log_levels,
                self.log_threads, self.log_date, level, *s)
        else: return self.info(*s, level=level)

    def warn(self, *s, level='warn'):
        if self.warn_fd: return PastlyLogger._log_file(
                self.warn_fd, self.warn_fd_mutex, self.log_levels,
                self.log_threads, self.log_date, level, *s)
        else: return self.notice(*s, level=level)

    def error(self, *s, level='error'):
        if self.error_fd: return PastlyLogger._log_file(
                self.error_fd, self.error_fd_mutex, self.log_levels,
                self.log_threads, self.log_date, level, *s)
        else: return self.warn(*s, level=level)

# pylama:ignore=E701
