#!/bin/bash


function install_packages(){
    # install_packages
    #  -install bash-completion required to use poertry bash-completion
    apt-get update -y && apt-get install -y  bash-completion

    echo 'source /etc/profile' >> ${HOME}/.bashrc
}

function install_poetry(){
    # install_poetry()
    # - installs latest version of poetry
    # - installs command completion for poetry
    pip install poetry
    poetry completions bash > /etc/bash_completion.d/poetry
}

function configure_git(){
    # this configure_git
    # - sets vscode as default editor for git
    # - sets git username if set in the .env file
    #  - sets git email if set in the .env file
    git config --global core.editor "code -w"

    if [ !  -z $GIT_USER ]
    then
        git config --global user.name "${GIT_USER}"
    fi

    if [ !  -z $GIT_EMAIL ]
    then
        git config --global user.email "${GIT_EMAIL}"
    fi
}

function install_git_bash_prompt(){
    # install_git_bash_prompt
    #  - install git bash prompt
    #  - configure git bash propmpt
    #  - enable git bash prompt
    if [ ! -d "${HOME}/.bash-git-prompt" ]
    then
        git clone https://github.com/magicmonty/bash-git-prompt.git  ${HOME}/.bash-git-prompt --depth=1

        echo 'if [ -f "${HOME}/.bash-git-prompt/gitprompt.sh" ]; then
        GIT_PROMPT_ONLY_IN_REPO=1
        source "$HOME/.bash-git-prompt/gitprompt.sh"
fi' >> ${HOME}/.bashrc

    fi
}

function install_poetry_packages(){
    # install poerty packages
    # - configure poetry to create virtual env with in project so that vscode can find python interpreter
    # - check if project file exist

    poetry config virtualenvs.in-project true


    if [ -f "poetry.lock" ]
    then
        poertry lock
    fi


    if [ -f "pyproject.toml" ]
    then
        poetry install
        poetry self add poetry-plugin-export
        poetry self add poetry-plugin-up
    fi
}

function install_pre-commit(){

    if [ -f ".pre-commit-config.yaml" ]
    then
        pre-commit autoupdate
        pre-commit installl
    fi

}

function main(){
    # main
    #  - execute functions in a given order
    install_packages
    install_poetry
    configure_git
    install_pre-commit
    install_git_bash_prompt
    install_poetry_packages
}

# call to main
main