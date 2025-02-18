
from flask import request, jsonify, Flask
import git
import os 
from flask_talisman import Talisman
import time

import hmac
import hashlib
#from waitress import serve #newly added. but also waitress does not provide ssl native

app = Flask(__name__) #run using "nohup flask run --host 0.0.0.0 #and note flask_app is an environment variable and you need kill -9 to kill flask server.  nohup is needed
#actually not.  flask run does not use the ssl certificates.
#so run 'nohup python3 server_update.py &
Talisman(app) 
SERVER_UPDATE=os.getenv("SERVER_UPDATE")

@app.route('/update_robot/<repname>', methods=['POST'])
def webhook(repname='onboarding_robot'):
    print("got update request")
    if(os.getenv("DEPLOY_"+repname,'17')=='17'):
        os.environ["DEPLOY_"+repname]='1' #default setting is to deploy
    if(os.getenv("DEPLOY_"+repname)!='1'):
        return 'ok, but no deploy of: '+repname, 200
    if request.method == 'POST':
        x_hub_signature = request.headers.get('X-Hub-Signature')
        if not is_valid_signature(x_hub_signature, request.data, SERVER_UPDATE):
            print("missing correct token/secret for server_update")
            return 'missing password', 400
        repo = git.Repo('~/robot/'+repname)
        print("repo:",repo) 
        origin = repo.remotes.origin
        print("origin:",origin)
        print("pulling:",origin.pull()) #not supposed to affect local files we changed that are not changed on parent
        print("... with secret") 
        os.environ["TIMEVERSION_"+repname]=str(int(time.time())) #
        os.system('bash '+'~/robot/'+repname+'/'+'aftergit') #for post merge to work, it need to be an execuatble. but this way it is easier to manage the post activities
        return 'Updated robot successfully', 200
    else:
        return 'Wrong event type', 400

@app.route('/version/<repname>', methods=['GET'])
def whatisversion(repname='onboarding_robot'):
    return jsonify(os.getenv("TIMEVERSION_"+repname,'17')+':'+os.getenv("DEPLOY_"+repname,'17'))
    
@app.route('/deploy/<repname>', methods=['GET']) 
def deploy(repname='onboarding_robot'):
    os.environ["DEPLOY_"+repname]='1'
    return 'ok', 200

@app.route('/nodeploy/<repname>', methods=['GET'])
def nodeploy(repname='onboarding_robot'):
    os.environ["DEPLOY_"+repname]='0'
    return 'ok', 200

@app.route('/gmail', methods=['POST'])
def gmailhooked():
    print('got a gmail call')
    os.system('bash '+'~/robot/'+'gmail_hook'+'/'+'readit')
    return 'ok called the prog', 200
@app.route('/test', methods=['GET'])
def testing():
    print('got a test call')
    return 'you asked for a test. i hope.', 200

@app.route('/.well-known/<fileaskedfor>', methods=['POST','GET'])
def https_stuff(fileaskedfor):
    print('they asked for',fileaskedfor) #if we want webroot renewal. but it is actually a subdirectory - acme-challenge. soc hange to "standalone" mode
    return 'lets not serve these yet', 200
    return send_from_directory('/etc/letsencrypt/live/robots.yakcollective.org',fileaskedfor, as_attachment=True)


def is_valid_signature(x_hub_signature, data, private_key):
    # x_hub_signature and data are from the webhook payload
    # private key is your webhook secret
    #print('signature=',x_hub_signature)
    #print("private key=",private_key)
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)
    
if __name__ == "__main__":
    app.run(host='0.0.0.0',ssl_context=('/etc/letsencrypt/live/robots.yakcollective.org/fullchain.pem', '/etc/letsencrypt/live/robots.yakcollective.org/privkey.pem'))
    #serve(app,host='0.0.0.0',port=5000, url_scheme='https')