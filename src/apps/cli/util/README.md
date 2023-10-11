Calling skill 'PM' function 'Readme' with file 'util/ToDoListSamplePrompt.txt'
{"variables":[{"key":"input","value":"I\u0027d like to build a typical Todo List Application: a simple productivity tool that allows users to create, manage, and track tasks or to-do items. \nKey features of the Todo List application include the ability to add, edit, and delete tasks, set due dates and reminders, categorize tasks by project or priority, and mark tasks as complete. \nThe Todo List applications also offer collaboration features, such as sharing tasks with others or assigning tasks to team members.\nAdditionally, the Todo List application will offer offer mobile and web-based interfaces, allowing users to access their tasks from anywhere."}]}
# Todo List Application

The Todo List Application is a simple productivity tool designed to help users create, manage, and track tasks or to-do items. With both mobile and web-based interfaces, users can access their tasks from anywhere, making it easy to stay organized and on top of their work.

## Features

- **Add, Edit, and Delete Tasks**: Users can easily create new tasks, modify existing ones, and remove tasks when they are no longer needed.
- **Set Due Dates and Reminders**: Users can set due dates for tasks and receive reminders to ensure they stay on track and complete tasks on time.
- **Categorize Tasks**: Users can organize tasks by project or priority, making it easy to focus on what's most important.
- **Mark Tasks as Complete**: Users can mark tasks as complete, providing a sense of accomplishment and helping to track progress.
- **Collaboration Features**: Users can share tasks with others or assign tasks to team members, making it easy to collaborate and work together on projects.
- **Mobile and Web-Based Interfaces**: Users can access their tasks from anywhere, whether they're on their phone or using a web browser.

## Architecture

The Todo List Application is organized into the following components:

- **Frontend**: The frontend is responsible for displaying the user interface and handling user interactions. It is built using a combination of HTML, CSS, and JavaScript, and communicates with the backend through a RESTful API.
- **Backend**: The backend is responsible for processing user requests, managing the database, and handling business logic. It is built using a server-side programming language (e.g., Node.js, Python, or Ruby) and a database management system (e.g., MySQL, PostgreSQL, or MongoDB).
- **Database**: The database stores all the data related to tasks, projects, and users. It is organized into tables or collections, depending on the chosen database management system.
- **API**: The API provides a set of endpoints for the frontend to interact with the backend. It follows the RESTful architecture, using standard HTTP methods (GET, POST, PUT, DELETE) to perform CRUD operations on tasks, projects, and users.
- **Authentication and Authorization**: The application includes user authentication and authorization features, ensuring that only authorized users can access and modify their tasks and projects.

## Running the Application

To run the Todo List Application, follow these steps:

1. Clone the repository to your local machine.
2. Install the required dependencies using the package manager for your chosen programming language (e.g., `npm install` for Node.js, `pip install -r requirements.txt` for Python, or `bundle install` for Ruby).
3. Set up the database by following the instructions provided in the `database_setup.md` file.
4. Start the backend server by running the appropriate command for your chosen programming language (e.g., `node server.js` for Node.js, `python manage.py runserver` for Python, or `rails server` for Ruby).
5. Open the frontend in your web browser by navigating to the provided URL (e.g., `http://localhost:3000`).

For more detailed instructions, refer to the `installation.md` and `usage.md` files included in the repository.
