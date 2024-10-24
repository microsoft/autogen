#!/bin/bash
# # Start a new tmux session named 'distributed_group_chat'
tmux new-session -d -s distributed_group_chat

# # Split the terminal into 2 vertical panes
tmux split-window -h

# # Split the left pane horizontally
tmux select-pane -t distributed_group_chat:0.0
tmux split-window -v 

# # Split the right pane horizontally
tmux select-pane -t distributed_group_chat:0.2
tmux split-window -v 

# Select the first pane to start
tmux select-pane -t distributed_group_chat:0.0

# Activate the virtual environment and run the scripts in each pane
tmux send-keys -t distributed_group_chat:0.0 "python run_host.py" C-m
tmux send-keys -t distributed_group_chat:0.2 "python run_writer_agent.py" C-m
tmux send-keys -t distributed_group_chat:0.3 "python run_editor_agent.py" C-m
tmux send-keys -t distributed_group_chat:0.1 "python run_group_chat_manager.py" C-m

# # Attach to the session
tmux attach-session -t distributed_group_chat
