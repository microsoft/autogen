param name string
param location string = resourceGroup().location
param tags object = {}

param allowedOrigins array = []
param applicationInsightsName string = ''
param appServicePlanId string
@secure()
param appSettings object = {}
param serviceName string = 'sk-func'
param storageAccountName string

module api '../core/host/functions.bicep' = {
  name: '${serviceName}-functions-dotnet-isolated-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    allowedOrigins: allowedOrigins
    alwaysOn: false
    appSettings: appSettings
    applicationInsightsName: applicationInsightsName
    appServicePlanId: appServicePlanId
    runtimeName: 'dotnet-isolated'
    runtimeVersion: '7.0'
    storageAccountName: storageAccountName
    scmDoBuildDuringDeployment: false
    managedIdentity: true
  }
}

var contributorRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')

resource rgContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, resourceGroup().id, contributorRole)
  properties: {
    roleDefinitionId: contributorRole
    principalType: 'ServicePrincipal'
    principalId: api.outputs.identityPrincipalId
  }
}

output SERVICE_API_IDENTITY_PRINCIPAL_ID string = api.outputs.identityPrincipalId
output SERVICE_API_NAME string = api.outputs.name
output SERVICE_API_URI string = api.outputs.uri
