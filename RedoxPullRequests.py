"""
Redox Application Coding Project
Zach Joyce

Build a tool to analyze pull request traffic for a Github organization. Write some code
that will retrieve all pull requests for the Ramda organization using the Github web API
and store the results in memory. Do not use a pre-existing Github library. We want to
see you interact directly with the Github API. Other than that, use whatever tools 
(language, frameworks, etc) you like, structure your code however you like, etc.
"""

import requests

# Constants used for accessing Github API
API_TOKEN = "token 5187c8dca503cd910c777a5d76e2253cec4f22e8"
GITHUB_ENDPOINT = "https://api.github.com/graphql"
TARGET_ORG = "ramda"
MAX_PAGE_SIZE = 100  # Set by Github API


# In-memory store of all pull requests. {PullRequestID : PullRequestObject}
PULL_REQUESTS = {}

QUERY = """
query orgLevel {{
  organization(login: "{org}") {{
    name
    repositories(first: {pageSize}, after: {rCursor}) {{
      nodes {{
        id
        name
        pullRequests(first: {pageSize}) {{
          nodes {{
            ...pullRequestFields
          }}
          ...pullConnection
        }}
      }}
      ...repoConnection
    }}
  }}
}}
query repoLevel {{
  repository(owner:"{org}", name:"{repoName}") {{
    id
    name
    pullRequests(first: {pageSize}, after: {pCursor}) {{
      nodes {{
        ...pullRequestFields
      }}
      ...pullConnection
    }}
  }}
}}

fragment pullConnection on PullRequestConnection {{
  totalCount
  pageInfo {{
    endCursor
    hasNextPage
  }}
}}

fragment repoConnection on RepositoryConnection {{
  totalCount
  pageInfo {{
    endCursor
    hasNextPage
  }}
}}

fragment pullRequestFields on PullRequest {{
# Summary Fields
  id
  url
  title
  number
  state
# Changes
  additions
  changedFiles
  deletions
# MetaData
  activeLockReason
  closed
  closedAt
  createdAt
  lastEditedAt
  locked
  merged
  mergeable
  mergedAt
  publishedAt
  repository {{name}}
  updatedAt
# Content
  bodyText
}}
"""


class PullRequest():
	def __init__(self, id):
		self.id = id
		
	def updateFromJSON(self, json):
		self.url = json.get("url", "")
		self.title = json.get("title", "")
		self.number = json.get("number", -1)
		self.state = json.get("state", "")
		self.additions = json.get("additions", 0)
		self.changedFiles = json.get("changedFiles", 0)
		self.deletions = json.get("deletions", 0)
		self.activeLockReason = json.get("activeLockReason", "")
		self.closed = json.get("closed", False)
		self.closedAt = json.get("closedAt", "")
		self.createdAt = json.get("createdAt", "")
		self.lastEditedAt = json.get("lastEditedAt", "")
		self.locked = json.get("locked", False)
		self.merged = json.get("merged", False)
		self.mergeable = json.get("mergeable", False)
		self.mergedAt = json.get("mergedAt", "")
		self.publishedAt = json.get("publishedAt", "")
		self.repository = json.get("repository", {}).get("name", "")
		self.updatedAt = json.get("updatedAt", "")
		self.bodyText = json.get("bodyText", "")
		

def call_api(query, opName, token=API_TOKEN):
	"""
	Handles a single call to the Github API using a GraphQL query
	query - The GraphQL query to send
	"""
	header = {"Authorization": token}
	json = {
		"query": query,
		"operationName": opName
	}
	request = requests.post(GITHUB_ENDPOINT, json=json, headers=header)
	
	if request.status_code != requests.codes.ok:
		raise Exception("Query Failed. Return code {}. {}".format(request.status_code, query))
	return request.json()
	

def load_pull_requests(token, org):
	"""
	Master process to orchestrate establishing the GraphQL query, 
	calling the API to retrieve all necessary data, and storing it in memory. 
	"""
	hasNextRepoPage = True
	repoCursor = "null"

	while hasNextRepoPage:
		query = QUERY.format(org=org, pageSize=MAX_PAGE_SIZE, repoName="", rCursor=repoCursor, pCursor="null")
		result = call_api(query, "orgLevel", token)

		repositories = result["data"]["organization"]["repositories"]
		for repo in repositories["nodes"]:
			process_repository(repo, token, org)
		
		# Adjust page cursor information
		pageInfo = repositories["pageInfo"]
		hasNextRepoPage = pageInfo["hasNextPage"]
		repoCursor = "\"{}\"".format(pageInfo["endCursor"])


def process_repository(repoJson, token, org):
	"""
	Process all pull requests for a single repository. Continue to query against
	subsequent pullRequest pages if necessary.
	"""
	repoName = repoJson["name"]
	continueProcessing = True
	
	while continueProcessing:
		# Process the current page of pull requests
		pullRequests = repoJson["pullRequests"]
		for pull in pullRequests["nodes"]:
			process_pull_request(pull)
		
		pageInfo = pullRequests["pageInfo"]
		continueProcessing = pageInfo["hasNextPage"]
		if not continueProcessing:
			break

		# Grab next page of pull request data to process
		pullCursor = "\"{}\"".format(pageInfo["endCursor"])
		
		query = QUERY.format(org=org, repoName=repoName, pageSize=MAX_PAGE_SIZE, rCursor="null", pCursor=pullCursor)
		result = call_api(query, "repoLevel", token)
		repoJson = result["data"]["repository"]
	
	
def process_pull_request(prJson):
	"""
	Creates a PullRequest object
	Translates the JSON query response into a local PullRequest object we can store.
	"""
	pullReq = PullRequest(prJson.get("id"))
	pullReq.updateFromJSON(prJson)

	PULL_REQUESTS[pullReq.id] = pullReq	
	

def main():
	load_pull_requests(API_TOKEN, TARGET_ORG)
	print("Number of Pull Requests - {}".format(len(PULL_REQUESTS)))
	print("Done")

# Run it
main()
