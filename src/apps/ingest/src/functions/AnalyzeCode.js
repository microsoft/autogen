const { app } = require("@azure/functions");

const Parser = require("tree-sitter");
const CSharp = require("tree-sitter-c-sharp");
const {Query, QueryCursor} = Parser
const parser = new Parser();
parser.setLanguage(CSharp);

app.http("AnalyzeCode", {
  methods: ["POST"],
  authLevel: "anonymous",
  handler: async (request, context) => {
    const sourceCode = await request.json();
    context.log(`File contents: ${sourceCode.Content}`);
    const tree = parser.parse(sourceCode.Content);
    // TODO: add a query to find all comments with classes
    const query = new Query(CSharp, `((comment) @comment
                                      [(method_declaration) @method-declaration
                                       (class_declaration) @class-declaration])`);
    
    const matches = query.matches(tree.rootNode);
    var items = [];
    for (let match of matches) {
      const captures = match.captures;
      var item = {};
      for (let capture of captures) {
        if (capture.name === 'comment') {
            item.Meaning = tree.getText(capture.node);
        }
        else if (capture.name === 'method-declaration') {
            item.CodeBlock = tree.getText(capture.node);
        }
        else if (capture.name === 'class-declaration') {
          item.CodeBlock = tree.getText(capture.node);
        }
      }
        items.push(item);
    }
    
    return { jsonBody: items};
  },
});
