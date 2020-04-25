#!/bin/sh

# Test all scripts

repo_root="$(pwd)"

python "$repo_root/examples/2-process-interaction/old.py" &&
    python "$repo_root/examples/2-process-interaction/new.py" &&
    python "$repo_root/examples/3-shared-resources/old.py" &&
    python "$repo_root/examples/3-shared-resources/new1.py" &&
    python "$repo_root/examples/3-shared-resources/new2.py" &&
    python "$repo_root/examples/4-preemptive-resource/old.py" &&
    python "$repo_root/examples/4-preemptive-resource/new.py" &&
    python "$repo_root/examples/4-preemptive-resource/v2.py" &&
    python "$repo_root/examples/4-preemptive-resource/v3.py" &&
    python "$repo_root/examples/4-preemptive-resource/v4.py" &&
    python "$repo_root/examples/nested_state_machine.py" &&
    python "$repo_root/examples/standalone_example.py" &&
    echo "Success" ||
    echo "Error"
