# Manual

## Installation

1. Download Grass v8.4

    ```shell
    sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
    sudo apt update
    sudo apt install grass=8.4.1-1~jammy1
    ```

2. Download the repo and replace raw scripts

    ```shell
    git clone https://github.com/ShiinaHiiragi/grass-gui
    sudo rm -r /usr/lib/grass84/gui/wxpython
    sudo mv ./grass-gui /usr/lib/grass84/gui/wxpython
    ```

## Memo
1. Spell for startup:

    ```shell
    gnome-terminal -- /bin/bash -ic "conda activate grass; LD_PRELOAD=/lib/x86_64-linux-gnu/libffi.so.7 FLASK_PORT=8000 /app/bin/grass --gui ~/grassdata/nc_basic_spm_grass7/PERMANENT"
    ```

2. Rite for debugging:

    ```python
    import gc
    from pprint import pprint
    rid = lambda num: [obj for obj in gc.get_objects() if id(obj) == num][0]
    ```

    try to print it:

    ```python
    print(f"import gc; from pprint import pprint; rid = lambda num: [obj for obj in gc.get_objects() if id(obj) == num][0]; frame=rid({id(frame)})")
    ```
