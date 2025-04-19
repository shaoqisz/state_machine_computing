## State Machine Computing

`State Machine Computing` is a Python project that simplifies the creation and management of state machines. It mainly relies on `qtpy5` and `transitions` libraries.

### Key Features
1. **Intuitive State Definition**: You can easily describe the nested relationships of states using a `JSON` file. After writing the `JSON` file, configure it in the `State Machine File`.
2. **Simple Transition Specification**: Define the behavior of transitions using a `JSON` file. Once the `JSON` file is written, configure it in the `Transitions Directory`.
3. **Customizable Transition Behavior**: Program the behavior when transitions occur by writing Python code. After writing the Python file, configure it in the `Custom Matter`.

### Prerequisites
Before you start using this project, make sure you have the following libraries installed:
- `qtpy5`
- `transitions`

You can install them using `pip`:
```bash
pip install qtpy5 transitions
```


### Configuration Steps
#### Step 1: Define States

1. Create a `JSON` file to describe the nested relationships of states. For example:

```json
[
    {
        "name": "statemachine",
        "children": [
            "state1", "state2", "state3"
        ],
        "initial": "state1"
    }
]
```
2. Configure the `JSON` file in the State Machine File.


#### Step 2: Define Transitions
1. Create a `JSON` file to describe the behavior of transitions. For example:
```json
[
    {"trigger": "trigger1", "conditions": "state1_state2_trans", "source": "statemachine_state1", "dest": "statemachine_state2"},
    {"trigger": "trigger2", "conditions": "state2_state3_trans", "source": "statemachine_state2", "dest": "statemachine_state3"},
    {"trigger": "trigger3", "conditions": "state3_state1_trans", "source": "statemachine_state3", "dest": "statemachine_state1"}
]
```
2. Configure the `JSON` file in the Transitions Directory.

#### Step 3: Define Custom Transition Behavior (Optional)

1. Write a Python file to define the behaviors of transitions, triggers, entrys, exits when transitions occur. For example:


```python
import sys

def state1_state2_trans(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append("Custom action is executed during the transition.")
    return True
```

2. Configure the Python file in the Custom Matter.


### Usage
After completing the above configuration steps, you can run the state machine program. The program will automatically load the configured state machine and transition rules and execute the custom actions as needed.

### Contribution
If you want to contribute to this project, please fork the repository, create a new branch, make your changes, and submit a pull request.