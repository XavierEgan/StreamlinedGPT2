from openai import OpenAI
import json
import os

client = OpenAI()

class Assistant:
    def __init__(self):
        # initialize variables
        self.message_history = []
        self.tools = []
        self.tool_references = {}
        self.tools_enabled = True
    
    def send_message(self, message, model, role="user", tool_call_id=None) -> str:
        # add the message to the messge history
        self._add_message(message, role, tool_call_id)

        # get the completion from the model
        if self.tools_enabled:
            response = client.chat.completions.create(messages=self.message_history, model=model, tools=self.tools).choices[0]
        else:
            response = client.chat.completions.create(messages=self.message_history, model=model).choices[0]

        # check if the model called a tool
        if not response.message.tool_calls:
            # there was no tool call, so just handle it normally
            self._add_message(response.message.content, "assistant", None)

            return response.message.content
        else:
            # there was a tool call and we need to handle it
            # first we need to add the assistants request to the message history
            self.message_history.append({
                "role":"assistant",
                "tool_calls":[
                    {
                        "id":f"{response.message.tool_calls[0].id}",
                        "type":"function",
                        "function":{
                            "arguments": f"{response.message.tool_calls[0].function.arguments}",
                            "name": f"{response.message.tool_calls[0].function.name}"}
                    }
                ]
            })

            # evaluate the tool
            tool_response = self._handle_tool(response)

            # add the tool to the chat history
            self._add_message(tool_response, "tool", response.message.tool_calls[0].id)

            # get the model response again (dont give it any tool options)
            response = client.chat.completions.create(messages=self.message_history, model=model).choices[0]
            self._add_message(response.message.content, "assistant", None)

            return response.message.content
        
    def add_tool(self, name:str, function, description:str, parameters:list[list[str]]):
        # build the tool with the given params
        self.tools.append({
            "type":"function",
            "function":{
                "name":f"{name}",
                "description":f"{description}",
                "parameters":{
                    "type":"object",
                    "properties":{
                        f"{param[0]}":{"type":param[1], "description":param[2]} for param in parameters
                    }
                }
            }
        })

        # create a reference to the tool function so we can call it later
        self.tool_references[name] = function

    def _handle_tool(self, response) -> str:

        tool_name = response.message.tool_calls[0].function.name
        arguments = response.message.tool_calls[0].function.arguments

        try:
            return str(self.tool_references[tool_name](**json.loads(arguments)))
        except Exception as e:
            raise Exception(f"Tool had error: {e}")

    def _add_message(self, message, role, tool_call_id=None):
        # if it has a tool call id then add it to the response so the api doesnt yell at me
        if not tool_call_id:
            self.message_history.append({"role":f"{role}", "content":f"{message}"})
        else:
            self.message_history.append({"role":f"{role}", "content":f"{message}", "tool_call_id":tool_call_id})
    
    def save(self, location):
        if not location[len(location)-5:] == ".json":
            location = f"{location}.json"
        
        try:
            with open(location, "w") as file:
                json.dump(self.message_history, file, indent=4)
                print(f"\033[32;1mSaved Message History to {location}\033[0m")
        except Exception as e:
            print(f"\033[31;1mError saving to '{location}'\nError: {e}\033[0m")

    def load(self, location):
        if not location[len(location)-5:] == ".json":
            location = f"{location}.json"
        
        try:
            with open(location, "r") as file:
                self.message_history = json.load(file)
                print(f"\033[32;1mLoaded Message History from {location}\033[0m")
        except Exception as e:
            print(f"\033[31;1mError loading '{location}'\nError: {e}\033[0m")

    def chatloop(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        model = "gpt-4o-mini"
        while True:
            user_input = input(f"\033[1;36mUSER > \033[22m")
            print(f"\033[0m", end="")

            if user_input[0] == "/":
                user_input = user_input[1:].lower()
                user_input = user_input.split(" ")

                command_word = user_input[0]
                args = user_input[1:]

                if command_word == "quit":
                    print(f"\033[1;31mQuitting... \033[0m")
                    break
                elif command_word == "change":
                    models = [
                        {"name": "gpt-4o-mini", "tools_enabled": True}, 
                        {"name": "gpt-4o", "tools_enabled": True}, 
                        {"name": "o1-mini", "tools_enabled": False}, 
                        {"name": "o1-preview", "tools_enabled": False}
                    ]

                    for i in range(len(models)):
                        print(f"{i}) {models[i]['name']}")
                    
                    new_model = input("which model do you want to change to > ")
                    try:
                        new_model = int(new_model)
                    except:
                        print("\033[1;31mI dont think thats a number\033[0m")

                    model = models[new_model]["name"]
                    self.tools_enabled = models[new_model]["tools_enabled"]

                    print(f"\033[32;1mModel changed to {model}\033[0m")

                elif command_word == "save":
                    if len(args) == 0:
                        print(f"\033[1;31mYou didnt give a location\033[0m")
                    
                    try:
                        self.save(args[0])
                    except Exception as e:
                        print(f"\033[1;31mError occured: {e}\033[0m")
                    
                elif command_word == "load":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    if len(args) == 0:
                        print(f"\033[1;31mYou didnt give a location\033[0m")
                    
                    try:
                        self.load(args[0])
                    except Exception as e:
                        print(f"\033[1;31mError occured: {e}\033[0m")
                    
                    for message in self.message_history:
                        if message["role"] == "user":
                            print(f"\033[36;1mUSER > \033[22m{message['content']}\033[0m")
                        elif message["role"] == "assistant" and message.get('content') is not None:
                            print(f"\033[32;1mASSISTANT > \033[22m{message['content']}\033[0m")
                            print("")
                        else:
                            continue

                elif command_word == "help":
                    help_text = '''
Available Commands:

quit:             Exits the program.
change:           Allows you to change the model being used.
save <location>:  Saves the current session to the specified location.
load <location>:  Loads a session from the specified location.
help:             Displays this help message.
system:           Sends lets you enter a system message.
context <file>:   Sends adds a file to the chat for context.
reset:            Resets the chat history and clears the screen.
                    '''
                    print(help_text)
                elif command_word == "system":
                    sys_message = input(f"\033[35;1mSYSTEM > \033[22m")
                    print(f"\033[0m", end="")

                    self._add_message(sys_message, "system")
                elif command_word == "context":
                    if len(args) == 0:
                        print(f"\033[1;31mYou didnt give a file location\033[0m")

                    self.send_message()
                elif command_word == "reset":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self.message_history = []
                    print(f"\033[32;1mChat Has Been Reset\033[0m")
                else:
                    print(f"\033[1;31mIDK What the command means\033[0m")
                continue

            response = self.send_message(user_input, model)
            print(f"\033[1;32mAssistant > \033[22m{response}\033[0m\n")

assistant = Assistant()
def think(thought) -> str:
    print(f"\033[33;1mTHOUGHT > \033[0m\033[33m{thought}\033[0m")
    return thought

# add a think tool as a test
assistant.add_tool(
    name="think",
    function=think,
    description="Returns whatever you put in it",
    parameters=[
        ["thought", "string", "The thought thats returned to you"]
        ]
)

assistant.chatloop()
