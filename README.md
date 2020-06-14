# Vipers

[![Version](https://img.shields.io/pypi/v/vipers)](https://pypi.org/project/vipers)
![License](https://img.shields.io/pypi/l/vipers)
![Support](https://img.shields.io/pypi/pyversions/vipers)

> Publish your vim plugin right away!

`Vipers` is VIM script publisher client.
Easily bundle and deploy to [vim.org](https://www.vim.org/scripts/index.php)
on command line.

No web browser required!


## Installation

```sh
pip install vipers
```

## Usage

```sh
# Create configuration file (vipers.json)
vipers init

# Bundle
vipers build .

# Publishing
vipers publish dist/*.tar.gz
```

## FAQ

> Why Python?

Because VIM supports python command (see `:help python`).
It will much easier when you develop your own VIM plugin using vipers module,
or even simple gluing in vimrc file; because it's written in Python.


## License

Copyright (C) 2020 Xvezda

MIT License
