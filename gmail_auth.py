import base64, hashlib, secrets, time, threading
from urllib.parse import urlencode
import requests
import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/gmail.compose']
@st.cache_resource
def state_store():
    return {}, threading.Lock()

def login_url(email):
    cfg=st.secrets['google_oauth']; states,lock=state_store()
    state=secrets.token_urlsafe(32); verifier=secrets.token_urlsafe(64)
    with lock:
        for k,v in list(states.items()):
            if time.time()-v[0]>600: states.pop(k,None)
        states[state]=(time.time(),email,verifier)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(dict(client_id=cfg['client_id'],redirect_uri=cfg['redirect_uri'],response_type='code',scope=' '.join(SCOPES),access_type='offline',prompt='consent',state=state,code_challenge=challenge,code_challenge_method='S256',login_hint=email))

def callback(email):
    if not any(k in st.query_params for k in ('code','error','state')): return
    code=st.query_params.get('code'); state=st.query_params.get('state'); st.query_params.clear()
    states,lock=state_store()
    with lock: record=states.pop(state,None)
    if not code or not record or time.time()-record[0]>600 or record[1]!=email:
        st.error('Autorización inválida o vencida. Conecta Gmail nuevamente.'); return
    try:
        cfg=st.secrets['google_oauth']
        r=requests.post('https://oauth2.googleapis.com/token',data=dict(code=code,client_id=cfg['client_id'],client_secret=cfg['client_secret'],redirect_uri=cfg['redirect_uri'],grant_type='authorization_code',code_verifier=record[2]),timeout=20); r.raise_for_status(); data=r.json()
        r=requests.get('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+data['access_token']},timeout=20); r.raise_for_status(); profile=r.json()
        if profile.get('email','').lower()!=email or profile.get('email_verified') is not True: raise ValueError('Cuenta no coincide')
        from datetime import datetime, timedelta
        cred=Credentials(token=data['access_token'],refresh_token=data.get('refresh_token'),token_uri='https://oauth2.googleapis.com/token',client_id=cfg['client_id'],client_secret=cfg['client_secret'],scopes=SCOPES,expiry=datetime.utcnow()+timedelta(seconds=int(data.get('expires_in',3600))))
        st.session_state['gmail_credentials']=cred; st.session_state['gmail_email']=email
    except Exception:
        st.error('No se pudo conectar Gmail. Verifica permisos y URL de retorno e inténtalo de nuevo.')

def sidebar():
    if 'google_oauth' not in st.secrets or 'auth' not in st.secrets:
        st.sidebar.info('Configura [auth] y [google_oauth] para crear borradores.'); return None
    if not st.user.is_logged_in:
        if st.sidebar.button('Iniciar sesión corporativa'): st.login()
        return None
    email=str(st.user.get('email','')).lower().strip()
    if not email.endswith('@casadorada.com') or st.user.get('email_verified') is not True:
        st.sidebar.error('Usa una cuenta corporativa verificada.'); st.session_state.pop('gmail_credentials',None)
        if st.sidebar.button('Cerrar sesión'): st.logout()
        return None
    callback(email)
    if st.sidebar.button('Cerrar sesión'):
        st.session_state.pop('gmail_credentials',None); st.session_state.pop('gmail_email',None); st.logout()
    cred=st.session_state.get('gmail_credentials') if st.session_state.get('gmail_email')==email else None
    if cred and not cred.valid:
        try: cred.refresh(Request())
        except Exception: cred=None; st.session_state.pop('gmail_credentials',None)
    if not cred:
        st.sidebar.link_button('Autorizar Gmail',login_url(email)); return None
    st.sidebar.success('Gmail conectado: '+email)
    if st.sidebar.button('Desconectar Gmail'):
        st.session_state.pop('gmail_credentials',None); st.session_state.pop('gmail_email',None); st.rerun()
    return email

def create_draft(msg):
    cred=st.session_state['gmail_credentials']
    return build('gmail','v1',credentials=cred,cache_discovery=False).users().drafts().create(userId='me',body={'message':{'raw':base64.urlsafe_b64encode(msg.as_bytes()).decode()}}).execute()
