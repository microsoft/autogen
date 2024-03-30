param containerAppsEnvironmentName string
param storageName string
param shareName string 
param location string
var storageAccountKey = listKeys(resourceId('Microsoft.Storage/storageAccounts', storageName), '2021-09-01').keys[0].value

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2022-11-01-preview' existing = {
  name: containerAppsEnvironmentName
}

var mountName = 'qdrantstoragemount'
var volumeName = 'qdrantstoragevol'
resource qdrantstorage 'Microsoft.App/managedEnvironments/storages@2022-11-01-preview' = {
  name: '${containerAppsEnvironmentName}/${mountName}'
  properties: {
    azureFile: {
      accountName: storageName
      shareName: shareName
      accountKey: storageAccountKey
      accessMode: 'ReadWrite'
    }
  }
}

resource qdrant 'Microsoft.App/containerApps@2022-11-01-preview' = {
  name: 'qdrant'
  location: location
  dependsOn:[
    qdrantstorage
  ]
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
        ingress: {
          external: true
          targetPort: 6333
        }
    }
    template: {
      containers: [
        {
          name: 'qdrant'
          image: 'qdrant/qdrant'
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          volumeMounts: [
            {
              volumeName: volumeName
              mountPath: '/qdrant/storage'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      volumes: [
        {
          name: volumeName
          storageName: mountName
          storageType: 'AzureFile'
        }
      ]
    }
  }
}

output fqdn string = qdrant.properties.latestRevisionFqdn

