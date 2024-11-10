## 🚀 Running UI in Dev Mode

Run the UI in dev mode (make changes and see them reflected in the browser with hotreloading):

- yarn install
- yarn start

This should start the server on port 8000.

## Design Elements

- **Gatsby**: The app is created in Gatsby. A guide on bootstrapping a Gatsby app can be found here - https://www.gatsbyjs.com/docs/quick-start/.
  This provides an overview of the project file structure include functionality of files like `gatsby-config.js`, `gatsby-node.js`, `gatsby-browser.js` and `gatsby-ssr.js`.
- **TailwindCSS**: The app uses TailwindCSS for styling. A guide on using TailwindCSS with Gatsby can be found here - https://tailwindcss.com/docs/guides/gatsby.https://tailwindcss.com/docs/guides/gatsby . This will explain the functionality in tailwind.config.js and postcss.config.js.

## Modifying the UI, Adding Pages

The core of the app can be found in the `src` folder. To add pages, add a new folder in `src/pages` and add a `index.js` file. This will be the entry point for the page. For example to add a route in the app like `/about`, add a folder `about` in `src/pages` and add a `index.tsx` file. You can follow the content style in `src/pages/index.tsx` to add content to the page.

Core logic for each component should be written in the `src/components` folder and then imported in pages as needed.

## connecting to front end

the front end makes request to the backend api and expects it at /api on localhost port 8081

## setting env variables for the UI

- please look at `.env.default`
- make a copy of this file and name it `.env.development`
- set the values for the variables in this file
  - The main variable here is `GATSBY_API_URL` which should be set to `http://localhost:8081/api` for local development. This tells the UI where to make requests to the backend.
