# Docker for Development

For developers contributing to the AutoGen project, we offer a specialized Docker environment. This setup is designed to streamline the development process, ensuring that all contributors work within a consistent and well-equipped environment.

## Autogen Developer Image (autogen_dev_img)

- **Purpose**: The `autogen_dev_img` is tailored for contributors to the AutoGen project. It includes a suite of tools and configurations that aid in the development and testing of new features or fixes.
- **Usage**: This image is recommended for developers who intend to contribute code or documentation to AutoGen.
- **Forking the Project**: It's advisable to fork the AutoGen GitHub project to your own repository. This allows you to make changes in a separate environment without affecting the main project.
- **Updating Dockerfile**: Modify your copy of `Dockerfile` in the `dev` folder as needed for your development work.
- **Submitting Pull Requests**: Once your changes are ready, submit a pull request from your branch to the upstream AutoGen GitHub project for review and integration. For more details on contributing, see the [AutoGen Contributing](https://microsoft.github.io/autogen/docs/Contribute) page.

## Building the Developer Docker Image

- To build the developer Docker image (`autogen_dev_img`), use the following commands:

  ```bash
  docker build -f .devcontainer/dev/Dockerfile -t autogen_dev_img https://github.com/microsoft/autogen.git#main
  ```

- For building the developer image built from a specific Dockerfile in a branch other than main/master

  ```bash
  # clone the branch you want to work out of
  git clone --branch {branch-name} https://github.com/microsoft/autogen.git

  # cd to your new directory
  cd autogen

  # build your Docker image
  docker build -f .devcontainer/dev/Dockerfile -t autogen_dev-srv_img .
  ```

## Using the Developer Docker Image

Once you have built the `autogen_dev_img`, you can run it using the standard Docker commands. This will place you inside the containerized development environment where you can run tests, develop code, and ensure everything is functioning as expected before submitting your contributions.

```bash
docker run -it -p 8081:3000 -v `pwd`/autogen-newcode:newstuff/ autogen_dev_img bash
```

- Note that the `pwd` is shorthand for present working directory. Thus, any path after the pwd is relative to that. If you want a more verbose method you could remove the "`pwd`/autogen-newcode" and replace it with the full path to your directory

```bash
docker run -it -p 8081:3000 -v /home/AutoGenDeveloper/autogen-newcode:newstuff/ autogen_dev_img bash
```

## Develop in Remote Container

If you use vscode, you can open the autogen folder in a [Container](https://code.visualstudio.com/docs/remote/containers).
We have provided the configuration in [devcontainer](https://github.com/microsoft/autogen/blob/main/.devcontainer). They can be used in GitHub codespace too. Developing AutoGen in dev containers is recommended.
