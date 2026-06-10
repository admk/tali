# tali.vim

Neovim / Vim syntax highlighting for [tali][tali].

## Screenshot

<p align="center">
  <img src="assets/example.png" alt="screenshot" width="500" />
</p>

## Installation

- [**lazy.nvim**][lazy.nvim] (for Neovim):
  ```lua
  {
    "admk/tali",
    ft = "tali",
    init = function(plugin)
      vim.opt.rtp:append(plugin.dir .. "/vim")
      vim.filetype.add({
        extension = { tali = "tali" },
      })
    end,
  },
  ```

- [**vim-plug**][vim-plug] (for Vim):
  ```vim
  call plug#begin('~/.vim/plugged')
    Plug 'admk/tali', { 'rtp': 'vim' }
  call plug#end()
  ```

[tali]: https://github.com/admk/tali
[lazy.nvim]: https://github.com/folke/lazy.nvim
[vim-plug]: https://github.com/junegunn/vim-plug
