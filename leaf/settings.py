import os

#: If set the client will be in "debug mode" and will show unhandled events etc
debug = os.environ.get("MATRIX_DEBUG", False)
