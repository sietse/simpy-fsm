#!/bin/sh

# Test all scripts

python=/home/sietse/lib/miniconda3/envs/sim/bin/python

cd examples

$python nested_state_machine.py > /dev/null &&
    $python simpy_statemachine.py > /dev/null &&
    $python simpy_2_charging.py > /dev/null &&
    $python simpy_3b_resource_manually.py > /dev/null &&
    $python simpy_3_resource.py > /dev/null &&
    $python simpy_4_machine_shop.py > /dev/null &&
    echo "Success" ||
    echo "Error"
