## How to run this

- Install [.NET SDK 8.0.302 ](https://dotnet.microsoft.com/en-us/download/dotnet)
- Install [Nodejs](https://nodejs.org/en/download/package-manager)
- Clone the repo (if you haven't already)
```bash
git clone https://github.com/microsoft/agnext.git
```
+ Switch to the branch
```bash
git checkout kostapetan/marketing-sample
```
+ Install node packages for the frontend
```bash
cd ./dotnet/samples/marketing-team/Marketing.Frontend
npm install
```
+ Add OpenAI Key and Endpoint
```bash
cd ..\Marketing.AppHost\
dotnet user-secrets set "OpenAI:Key" "your_key"
dotnet user-secrets set "OpenAI:Endpoint" "https://your_endpoint.openai.azure.com/"
```
+ Run the application
```bash
dotnet run
```