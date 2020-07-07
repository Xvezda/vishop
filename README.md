# Vishop

[![Version](https://img.shields.io/pypi/v/vishop)](https://pypi.org/project/vishop)
![License](https://img.shields.io/pypi/l/vishop)
![Support](https://img.shields.io/pypi/pyversions/vishop)

> Publish your vim plugin right away!

Vishop (**VI**M **S**cript **Ho**st **P**ublisher) is VIM script publisher client.
Easily bundle and deploy to [vim.org](https://www.vim.org/scripts/index.php)
on command line.

![Demo](https://gist.githubusercontent.com/Xvezda/cf7adb8b8fa22aadbece8d8329d13dfa/raw/vim-readonly.gif)

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

> Inspirations?

Inspired by many of dependency, package managers and publish, deployment tools.
Such as [twine](https://pypi.org/project/twine), [yarn](https://yarnpkg.com/) and [npm](https://docs.npmjs.com/cli/npm).


## Badge

Add the badge to your project's `README.md`:
```markdown
[![Script manager: vishop](https://img.shields.io/badge/script%20manager-vishop-blueviolet)](https://github.com/Xvezda/vishop)
```

[![Script manager: vishop](https://img.shields.io/badge/script%20manager-vishop-blueviolet)](https://github.com/Xvezda/vishop)


## License

Copyright (C) 2020 Xvezda

MIT License
