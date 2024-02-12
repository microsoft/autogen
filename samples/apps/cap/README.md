**Composable Actor Platform (CAP) for Autogen**

**Python Instructions**
0) cd py
1) pip install -r ./py/requirements.txt
2) python ./py/src/demo/app.py

Notes:
1) Options 3,4,5&6 require OAI_CONFIG_LIST for Autogen.  
   Autogen python requirements: 3.8 <= python <= 3.11
2) For option 2, type something in and see who receives the message.  Quit to quit.
3) For any option that display an chart (like option 4), docker code execution will need to be disabled to see it. (set environment variable AUTOGEN_USE_DOCKER to False)

Reference:
```
Select the demo app to run:
1. CAP Hello World
2. CAP Complex Agent (e.g. Name or Quit)
3. AutoGen Pair
4. CAP AutoGen Pair
5. AutoGen GroupChat
6. CAP AutoGen GroupChat
Enter your choice (1-6):
```

**TODO**
![Todo List](Todo.md)
