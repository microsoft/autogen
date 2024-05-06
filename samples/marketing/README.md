# [In progress] Marketing Saple application

This is a demo application that showcase the different features of the AI Agent framework.
There are five agents in this application that control the different areas of the UI autonomously.

The agents are designed to be able to interact with each other and the user to achieve their goals.
To do that each agent has 

![Agents](readme-media/screenshot.png)

![Agents](readme-media/agents.png)

## Requirements to run locally
### Frontend
The latest version of Node.js and npm

### Backend
Visual Studio or Visual Studio code and the latest version of dotnet

## Running with azd
To run the application with azd, you need to have the azd cli installed. You can install it following the instructions here:

https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd?tabs=winget-windows%2Cbrew-mac%2Cscript-linux



Then you can run the following command to start the application:
```powers

## How to run the application locally

Execute Run.ps1. IF you are missing the config file the script will create an empty one for you and ask you to fill it out.
```
.\run.ps1 
```

## How to debug the application locally
To debug the backend, you can simply open the solution in Visual Studio, and press F5 to start debugging.
Remember to copy `appsettings.local.template.json` to `appsettings.json` and fill out the values.</p>
The frontend is a NodeJS React application. You can debug it using Visual Studio code.