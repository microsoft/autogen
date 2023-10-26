metadata description = 'Creates an Azure Cosmos DB account.'
param name string
param location string = resourceGroup().location
param tags object = {}

param connectionStringKey string = 'AZURE-COSMOS-CONNECTION-STRING'

@allowed([ 'GlobalDocumentDB', 'MongoDB', 'Parse' ])
param kind string

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2022-08-15' = {
  name: name
  kind: kind
  location: location
  tags: tags
  properties: {
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    apiProperties: (kind == 'MongoDB') ? { serverVersion: '4.0' } : {}
    capabilities: [ { name: 'EnableServerless' } ]
  }
}


output connectionStringKey string = connectionStringKey
output endpoint string = cosmos.properties.documentEndpoint
output id string = cosmos.id
output name string = cosmos.name
