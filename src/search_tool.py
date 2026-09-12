import os
from exa_py import Exa

exa=Exa(api_key=os.getenv('EXA_API_KEY'))

def search_web(query:str,num_results: int=5)->list[dict]:
    # common use search funtion to search the web using given query and return list of result
    results=exa.search(query,num_results=num_results)
    return [
        {"title":r.title,"url":r.url,"snippet":getattr(r,"text","")}
        for r in results.results
    ]