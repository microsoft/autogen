module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  // Only run files that end with .test.ts or .spec.ts
  testMatch: [
    '**/test/**/*.test.ts',
    '**/test/**/*Test.ts',
    '**/test/**/*.spec.ts'
  ],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: 'tsconfig.json'
    }]
  }
};
