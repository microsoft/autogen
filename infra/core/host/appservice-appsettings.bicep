@description('The name of the app service resource within the current resource group scope')
param name string

@description('The app settings to be applied to the app service')
@secure()
param appSettings object

resource appService 'Microsoft.Web/sites@2022-03-01' existing = {
  name: name
}

resource settings 'Microsoft.Web/sites/config@2022-03-01' = {
  name: 'appsettings'
  parent: appService
  properties: appSettings
}
