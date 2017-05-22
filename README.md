# Matrix Leaf

A Matrix client with simplicity in mind. This means:

* Only a subset of the spec is supported
* One client => one room
* Minimalistic interface

## Usage

    docker run -ti simonklb/matrix-leaf

*If your username is __not__ already registered on the server and user
registration is enabled on the homeserver you will automatically be
registered.*

*If you try to join a room that does not already exist the room will be
automatically created.*

### Available environment variables

    MATRIX_HOSTNAME
    MATRIX_USERNAME
    MATRIX_PASSWORD # Be careful when using clear text passwords
    MATRIX_ROOM

    # Shows debug messages such as unhandled events data and also logs debug
    # output to a file named debug.log
    MATRIX_DEBUG

Example:

    docker run -ti -e MATRIX_HOSTNAME='https://matrix.org' \
        -e MATRIX_USERNAME='neo' -e MATRIX_ROOM='#matrix:matrix.org' \
        simonklb/matrix-leaf

You could also store the environment variables in a file and run:

    docker run -ti --env-file matrix.env simonklb/matrix-leaf
