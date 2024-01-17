#!/bin/bash

# load the first argument provided to the script
mode=$1
SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

VIRTUAL_ENV_VALUE="$VIRTUAL_ENV"
CONDA_PREFIX_VALUE="$CONDA_PREFIX"

# if mode is not provided, set it to default proceed with code below
if [ -z "$mode" ]; then
    mode="main"
fi


# if mode is set to "main", print hello
if [ "$mode" == "main" ]; then
    # Check if a tmux session with the name tinyRAtmux is already running
    # if it is, detach it and attach it to the current terminal
    # if it is not, proceed to create a new session using the custom configuration
    tmux has-session -t tinyaRAtmux 2>/dev/null
    if [ $? -eq 0 ]; then
        # Detach the session if already running
        tmux detach-client -s tinyaRAtmux
        tmux attach-session -t tinyaRAtmux
        exit 0;
    fi

    # Path to the custom tmux configuration file
    TMUX_CONFIG=tinyra-tmux.conf

    # Create a new tmux session using the custom configuration
    tmux new-session -d -s tinyaRAtmux
    tmux source-file $SCRIPTS_DIR/$TMUX_CONFIG

    # If VIRTUAL_ENV_VALUE is not empty, export it
    if [ -n "$VIRTUAL_ENV_VALUE" ]; then
        CMD1="export VIRTUAL_ENV=$VIRTUAL_ENV_VALUE && "
    fi

    # If CONDA_PREFIX_VALUE is not empty, export it
    if [ -n "$CONDA_PREFIX_VALUE" ]; then
        CMD1+="conda activate $CONDA_PREFIX_VALUE && "
    fi

    CMD1+="export TERMCOLOR=truecolor && python $SCRIPTS_DIR/tui.py"
    tmux send-keys -t tinyaRAtmux:0 "$CMD1" C-m
    tmux rename-window -t tinyaRAtmux:0 "main"

    tmux select-window -t tinyaRAtmux:0
    tmux attach-session -t tinyaRAtmux
fi

# if mode is set to "tab" print hell

if [ "$mode" == "tab" ]; then
    # get the second argument provided to the script
    msgid=$2
    echo "Adding a new tab to the tmux session"
    # add a new tab to the tmux session called tinyRAtmux
    newtab="tab-$msgid"
    # check if a tab with the name newtab already exists
    tmux list-windows -t tinyaRAtmux | grep $newtab
    if [ $? -eq 0 ]; then
        # if it does, refuse to add a new tab
        echo "Tab $newtab already exists"
        exit 0;
    fi

    # if it does not, add a new tab to the tmux session at the end
    tmux new-window -t tinyaRAtmux -n $newtab
    tmux select-window -t tinyaRAtmux:$newtab
     # If VIRTUAL_ENV_VALUE is not empty, export it
    if [ -n "$VIRTUAL_ENV_VALUE" ]; then
        CMD1="export VIRTUAL_ENV=$VIRTUAL_ENV_VALUE && "
    fi

    # If CONDA_PREFIX_VALUE is not empty, export it
    if [ -n "$CONDA_PREFIX_VALUE" ]; then
        CMD1+="conda activate $CONDA_PREFIX_VALUE && "
    fi
    CMD1+="export TERMCOLOR=truecolor && python $SCRIPTS_DIR/run_tab.py $msgid && exit"
    tmux send-keys -t tinyaRAtmux:$newtab "$CMD1" C-m
fi
