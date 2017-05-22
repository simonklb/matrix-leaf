from functools import partial, wraps
import queue
import threading


class OP:
    """
    A client operation.

    :param client: The client this operation is executed from.
    :type client: :class:`leaf.client.Client`
    :param func: The operation function that is going to be executed.
    :type func: function
    :param require_connection: If require_connection is true and the client
                               is not connected an error message will be drawn
                               on the UI.
    :type require_connection: bool
    """
    def __init__(self, client, func, require_connection):
        self.client = client
        self.func = func
        self.require_connection = require_connection

    def __call__(self, *args, **kwargs):
        if self.require_connection and not self.client.connected:
            self.client.ui.draw_client_info("Error: Not connected to server")
            self.client.show_help("connect")
            return

        self.func(self.client, *args, **kwargs)


def op(func=None, require_connection=True):
    """
    A decorator which enqueues the decorated method into the
    :class:`OPExecutor` thread when called.

    The object which the decorated method belongs to needs to have an
    :class:`OPExecutor` object attribute named `op_executor`.

    :param require_connection: If the operation requires the client to be
                               connected to the server when it's executed.
    :type require_connection: bool
    """
    if func is None:
        return partial(op, require_connection=require_connection)

    @wraps(func)
    def decorator(self, *args, **kwargs):
        op = OP(self, func, require_connection)
        self.op_executor.enqueue(op, *args, **kwargs)
    return decorator


class OPExecutor(threading.Thread):
    """
    Thread used for executing long-running operations in the client.

    :var exception_handler: Callback which handles exceptions for operation
                            executions.
    :vartype exception_handler: function
    """
    def __init__(self, exception_handler):
        super().__init__()

        self.stop_event = threading.Event()
        self.queue = queue.Queue()
        self.exception_handler = exception_handler

    def enqueue(self, op, *args, **kwargs):
        """
        Push an operation into the queue to be executed later.

        :param op: The operation to be queued for execution
        :type op: :class:`OP`
        """
        self.queue.put(partial(op, *args, **kwargs))

    def run(self):
        while not self.stop_event.isSet():
            try:
                self.queue.get(timeout=0.5)()
            except queue.Empty:
                pass
            except Exception as exc:
                self.exception_handler(exc)

    def stop(self):
        """
        Stop the thread.
        """
        if self.isAlive():
            # Toggle shutdown of the executor
            self.stop_event.set()

            # Wait for all queued operations to finish
            self.join()
