# Manual

1. Download Grass v8.4

    ```shell
    sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
    sudo apt update
    sudo apt install grass
    ```

2. Download the repo and replace raw scripts

    ```shell
    git clone https://github.com/ShiinaHiiragi/grass-gui
    sudo rm -r /usr/lib/grass84/gui/wxpython
    sudo mv ./grass-gui /usr/lib/grass84/gui/wxpython
    ```
