# Vishop

[![Version](https://img.shields.io/pypi/v/vishop)](https://pypi.org/project/vishop)
![License](https://img.shields.io/pypi/l/vishop)
![Support](https://img.shields.io/pypi/pyversions/vishop)

> Publish your vim plugin right away!

`vishop` is VIM script publisher client.
Easily bundle and deploy to [vim.org](https://www.vim.org/scripts/index.php)
on command line.

![Demo](https://gist.githubusercontent.com/Xvezda/cf7adb8b8fa22aadbece8d8329d13dfa/raw/65fefd4b624fdbf943b83c62c1ef4a26ff652e80/vim-readonly.gif)

No web browser required!


## Installation

```sh
pip install vishop
```

## Usage

```sh
# Create configuration file (vishop.json)
vishop init

# Bundle
vishop build .

# Publishing
vishop publish dist/*.tar.gz
```

## FAQ

> Why Python?

Because VIM supports python command (see `:help python`).
It will much easier when you develop your own VIM plugin using vishop module,
or even simple gluing in vimrc file; because it's written in Python. And also _life is short_.


## License

Copyright (C) 2020 Xvezda

MIT License
