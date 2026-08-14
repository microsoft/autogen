## How to build and run the website

### Prerequisites
- dotnet 7.0 or later

### Build
Firstly, go to autogen/dotnet folder and run the following command to build the website:
```bash
dotnet tool restore
dotnet tool run docfx website/docfx.json --serve
```

After the command is executed, you can open your browser and navigate to `http://localhost:8080` to view the website.