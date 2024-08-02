import openai
import boto3
import json
import uuid
from uuid import UUID


def query_openai(input_prompt):
  
    openai.api_key = "openAI API KEY"

    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": input_prompt}])
    nested_json = completion.choices[0].message.content

    return nested_json
    
def extract_json_from_text(text):
    start_index = text.find('{')
    end_index = text.rfind('}')
    
    if start_index == -1 or end_index == -1:
        return None  # No JSON object found in the text
    
    json_str = text[start_index:end_index+1]
    return json_str

def fix_invalid_json_trail(json_str):
    brace_count = 0
    bracket_count = 0
    cut_index = None

    for i, c in enumerate(json_str):
        if c == '{':
            brace_count += 1
        elif c == '}':
            brace_count -= 1
        elif c == '[':
            bracket_count += 1
        elif c == ']':
            bracket_count -= 1

        # When both counters are zero, it's a potential valid end point for the JSON string.
        if brace_count == 0 and bracket_count == 0:
            cut_index = i + 1  # +1 to include the current '}' or ']'

    if cut_index is not None:
        # Cut the string at the found index
        json_str = json_str[:cut_index]
        
        try:
            json_obj = json.loads(json_str)
            return json_obj
        except json.JSONDecodeError:
            return None

    return None


def get_from_s3(uuivd4_key):
    # Requirements: uuid
    s3 = boto3.client("s3")
    BUCKET_NAME = "mapitdata"

    response = s3.get_object(
        Bucket=BUCKET_NAME, Key=uuivd4_key
    )  # trying to get response from s3 bucket
    data = response["Body"].read().decode("utf-8")  # finding file content if exists
    
    return json.loads(data)


def store_in_s3(uuivd4_key, keywords, nested_json):
    s3 = boto3.client("s3")
    BUCKET_NAME = "mapitdata"

    data = {"key": uuivd4_key, "input": keywords, "output": nested_json}

    s3.put_object(Body=json.dumps(data), Bucket=BUCKET_NAME, Key=uuivd4_key)
    return data


base_input_prompt = '''You are an educational assistant that generates a mindmap to help a student in a specific subject. The user inputs a list of keywords. Your task is to
1. analyze the inputs, and find the central keyword or topic that encompasses the input keywords.
2. come up with 2 related terminologies, keywords, or concepts that branches out from your central topic.
After coming up with the related words, repeat the same process for each of the words, so it keeps branching out. Here are the rules you must keep.
-Ensure that ALL generated concepts or keywords are related to the input but REFRAIN from including the input keywords themselves. For example, if you input "calculus", then "calculus" or "Calculus" cannot be one of your outputs.
-There MUST be no overlap between any input keywords or generated words.
-You MUST only output your result in a nested JSON format with keys "keyword", "description", and "children".
-Do not add anything else to the output.
An example is given below to help your understanding. In the example below, the content of most descriptions were abbreviated for the sake of space but you must give a one-sentence definition for the keywords for all keywords in the actual output. Only output your result like the given example delimited inside ### but DO NOT INCLUDE THE DELIMITER IN YOUR OUTPUT.
Example>
INPUT: ["Integration", "Differentation", "Central Limit Theorem"]
OUTPUT:
###
{"keyword":"Calculus","description":"Calculus is a branch of mathematics that studies continuous change, primarily through derivatives and integrals.",
"children":[{"keyword":"Differential Calculus","description":"Differential Calculus focuses on the concept of a derivative, which represents an instantaneous rate of change.",
"children":[{"keyword":"Limits","description":"..."},
{"keyword":"Derivatives","description":"...",
"children":[{"keyword":"Chain Rule","description":"..."},
{"keyword":"Implicit Differentiation","description":"..."},
{"keyword":"Partial Differentiation","description":"..."}]},
{"keyword":"Applications of Derivatives","description":"...",
"children":[{"keyword":"Optimization","description":"..."},
{"keyword":"Related Rates","description":"..."},
{"keyword":"Tangent Lines","description":"..."},
{"keyword":"L'Hôpital's Rule","description":"..."}]}]},
{"keyword":"Integral Calculus","description":"...",
"children":[{"keyword":"Antiderivatives","description":"..."},
{"keyword":"Definite Integrals","description":"...",
"children":[{"keyword":"Fundamental Theorem of Calculus","description":"..."},
{"keyword":"Area between Curves","description":"..."}]},
{"keyword":"Applications of Integrals","description":"...",
"children":[{"keyword":"Area under Curves","description":"..."},
{"keyword":"Volume of Solids","description":"..."},
{"keyword":"Work and Accumulation","description":"..."},
{"keyword":"Arc Length","description":"..."}]}]},
{"keyword":"Multivariable Calculus","description":"...",
"children":[{"keyword":"Partial Derivatives","description":"..."},
{"keyword":"Multiple Integrals","description":"...",
"children":[{"keyword":"Double Integrals","description":"..."},
{"keyword":"Triple Integrals","description":"..."}]},
{"keyword":"Vector Calculus","description":"...",
"children":[{"keyword":"Gradient","description":"..."},
{"keyword":"Divergence","description":"..."},
{"keyword":"Curl","description":"..."},
{"keyword":"Stokes' Theorem","description":"..."},
{"keyword":"Green's Theorem","description":"..."}]}]},
{"keyword":"Sequences and Series","description":"...",
"children":[{"keyword":"Convergence and Divergence","description":"..."},
{"keyword":"Taylor Series","description":"..."},
{"keyword":"Power Series","description":"..."}]},
{"keyword":"Differential Equations","description":"...",
"children":[{"keyword":"First-Order Differential Equations","description":"..."},
{"keyword":"Second-Order Differential Equations","description":"..."},
{"keyword":"Systems of Differential Equations","description":"..."},
{"keyword":"Boundary Value Problems","description":"..."}]}]}
###
'''
update_input_prompt = '''You are an educational assistant that generates a mindmap to help a student in a specific subject. The user inputs a keyword and a nested JSON object. Your task is to come up with 2 related terminologies, keywords, or concepts that branches out from the input keyword. If user's keyword is not in JSON object's keywords, just add it under the first keyword in the JSON object.
-Ensure that ALL generated concepts or keywords are related to the input but REFRAIN from including the input keywords themselves. For example, if you input "calculus", then "calculus" or "Calculus" cannot be one of your outputs.
-There MUST be no overlap between any input keywords or generated words.
-You MUST only output your result in a nested JSON format with keys "keyword", "description", and "children".
-Do not add anything else to the output.
An example is given below to help your understanding. In the example below, the content of descriptions were abbreviated for the sake of space but you must give a one-sentence definition for the keywords for all keywords in the actual output. Only output your result like the given example delimited inside ### but DO NOT INCLUDE THE DELIMITER IN YOUR OUTPUT.
Example>
INPUT: {"keyword":"Psychology","description":"...","children":[{"keyword":"Cognition", "description":"..."}]}, Psychology

OUTPUT:
###
{"keyword":"Psychology","description":"...","children":[{"keyword":"Cognition","description":"..."},{"keyword":"Memory", "description":"..."},{"keyword":"Conditioning","description":"..."}]}
###
'''


def lambda_handler(event, context):

    pathParameters = event.get("pathParameters", {})

    if pathParameters:

        action = pathParameters.get("action")

        if action == "create":
            uuivd4_key = str(uuid.uuid4())  # making a new key for the data
            body = event["body"]
            
            if body == None:
                return {"statusCode": 200, "body": "No data could be found"}
            
            body_json = json.loads(body)
            keywords = body_json["keywords"]
        

            input_prompt = (
                base_input_prompt
                + f"\nFollowing the aforementioned example and instructions, give your output for the subsequent input: \n{keywords}"
            )
            
            nested_json = query_openai(input_prompt)
            parsed_json = fix_invalid_json_trail(extract_json_from_text(nested_json))
            print(nested_json)
            #parsed_json = json.loads(nested_json)

            data = store_in_s3(uuivd4_key, keywords, parsed_json)
            return {"statusCode": 200, "body": json.dumps(data)}

        if action == "read":
            uuivd4_key = event["queryStringParameters"]["key"]
            if uuivd4_key == None:
                return {"statusCode": 200, "body": "No key could be found"}
            data = get_from_s3(uuivd4_key)
            return {"statusCode": 200, "body": json.dumps(data)}

        if action == "update":
          
            # Getting key
            uuivd4_key = event["queryStringParameters"]["key"]
            if uuivd4_key == None:
              return {"statusCode": 200, "body": "No key could be found"}
            data = get_from_s3(uuivd4_key)
          
            # Getting keyword data
            body = event["body"]
            if body == None:
                return {"statusCode": 200, "body": "No data could be found"}
            body_json = json.loads(body)
            
            keywords = body_json["keywords"]
            stored_keywords = data["input"]
                
            
            keywords = [
                keyword for keyword in keywords if keyword not in stored_keywords
            ]  # just removes duplicates from the keywords
            
            keywords = stored_keywords + keywords
            
            input_prompt = (
                update_input_prompt
                + f"\nFollowing the aforementioned example and instructions, give your output for the subsequent input: {body_json} {keywords}"
            )
            
            nested_json = query_openai(input_prompt)
            parsed_json = fix_invalid_json_trail(extract_json_from_text(nested_json))
            #parsed_json = json.loads(nested_json)
            data = store_in_s3(uuivd4_key, keywords, parsed_json)
            
            return {"statusCode": 200, "body": json.dumps(data)}

    else:
        return {"statusCode": 200, "body": "No url provided"}
