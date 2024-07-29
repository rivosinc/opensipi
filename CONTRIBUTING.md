<!--
SPDX-FileCopyrightText: © 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Preparations
There are several tools to be installed first.
 - ```poetry```

   ```poetry``` is recommended to establish the virtual environment for developers. This simplifies the installation of OpenSIPI and ensures all devlopers are using exactly the same versions of Python, modules, and packages so that compatibility won't be a concern. Please read [here](https://python-poetry.org/docs/) to install ```poetry```.

 - ```reuse```

   ```reuse``` is used to manage the licensing for each specific file in this project. Please read [here](https://reuse.software/faq/#install-tool) to install ```reuse```.

 - ```pre-commit```

   ```pre-commit``` is used to ensure some basic commit checks are done locally. Please read [here](https://github.com/riscv/docs-spec-template?tab=readme-ov-file#enabling-pre-commit-checks-locally) to install ```pre-commit```.

# Make Contributions
Assume the contributors are familiar with the basics of git and GitHub.com. To contribute to the codes and documentation of this project, please follow the detailed instructions [here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) to fork a repo to your own GitHub account, clone your fork to your local computer, and configure git to sync your fork with the upstream repo. Push updates to your own fork first and create a pull request (PR) to merge your updates to the original repo.

There are various ways to work on the project. If you happen to use [Visual Studio Code](https://code.visualstudio.com/) (VSC) as your integrated development environment (IDE), here is how to enable the ```poetry``` virtual environment. In VSC, open the ```opensipi``` root dir, where ```pyproject.toml``` file is located. In the VSC terminal window, use the following command to install the virtual environment for ```opensipi``` project.

```
poetry install
```

It's recommended to re-install ```opensipi``` each time your fork is synced with the origin repo.

Next, in the VSC terminal window, type in the following command to activate the virtual environment.

```
poetry shell
```

Now click the default interpreter at bottom right corner of VSC as shown below.

![image](/docs/Figures/VSC_BR.png)

A dialog pops up in the top center of VSC and prompt you to select from the avaialble interpreters. Choose the one containing "opensipi" in the name.

![image](/docs/Figures/VSC_top.png)

You're all set to make changes!

Once you're done with changes. Use the below command to check if all files under ```opensipi``` root dir carry a license. This step is optional. You need to run it only if you add additional files to the root dir.

```
reuse lint
```

Before committing your updates, run the pre-commit checks as shown below.

```
pre-commit run
```
