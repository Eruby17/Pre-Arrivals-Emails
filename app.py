import base64, html, re
from pathlib import Path
from urllib.parse import urlencode, urlparse
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from io import BytesIO
from email.message import EmailMessage
from email import policy
from email.utils import formataddr
from gmail_auth import sidebar, create_draft

st.set_page_config(page_title='Casa Dorada | Email Studio',layout='wide')
gmail_email=sidebar()
ROOT=Path(__file__).parent
NAVY='#092b63'; SAND='#f7f4ee'

def esc(s): return html.escape(str(s),quote=True)
def paragraphs(s): return esc(s).replace('\n','<br>')
def money(v): return f'${v:,.2f} USD'
def get_image(key, upload, url):
    if url.strip():
        u=urlparse(url.strip())
        if u.scheme=='https' and u.netloc: return ('url',url.strip())
        st.warning(f'URL de {key} inválida; se usará una imagen local.')
    if upload:
        try:
            im=Image.open(upload).convert('RGB'); im.thumbnail((1200,1200)); b=BytesIO(); im.save(b,format='JPEG',quality=85); return ('bytes',b.getvalue())
        except Exception: st.warning(f'Imagen de {key} inválida; se usará la original.')
    return ('bytes',(ROOT/'assets'/f'{key}.jpg').read_bytes())

def build(d, images, mode='html'):
    used=set()
    def image(key, alt, width=600):
        used.add(key); kind,val=images[key]
        src=val if kind=='url' else ('cid:'+key+'@casadorada.local' if mode=='eml' else 'data:image/jpeg;base64,'+base64.b64encode(val).decode())
        return f'<img src="{esc(src)}" alt="{esc(alt)}" width="{width}" style="display:block;width:100%;max-width:{width}px;height:auto;border:0;">'
    def cta(label,service,secondary=False):
        link='mailto:'+d['email']+'?'+urlencode({'subject':f'{service} | Reservation {d["reservation"]}','body':f'Hello Casa Dorada Reservations,\nI am interested in {service}.\nReservation: {d["reservation"]}\nThank you.'}).replace('+','%20')
        if secondary:
            return f'<p style="margin:12px 0 0;"><a href="{esc(link)}" style="color:{NAVY};font-size:14px;font-weight:bold;text-decoration:underline;">{esc(label)} &rarr;</a></p>'
        return f'<table role="presentation" align="center" cellspacing="0" cellpadding="0"><tr><td bgcolor="{NAVY}" style="border-radius:4px;"><a href="{esc(link)}" style="display:inline-block;padding:15px 24px;color:#ffffff;font-size:16px;font-weight:bold;text-decoration:none;">{esc(label)}</a></td></tr></table>'
    def block(content,bg='#ffffff',padding='26px'):
        return f'<tr><td bgcolor="{bg}" style="padding:{padding};text-align:center;font-family:Arial,sans-serif;color:#243445;font-size:16px;line-height:1.55;">{content}</td></tr>'
    def heading(s): return f'<h2 style="font-family:Georgia,serif;font-weight:normal;font-size:29px;line-height:1.2;color:{NAVY};margin:8px 0 15px;">{esc(s)}</h2>'
    def price(s): return f'<p style="font-size:27px;color:{NAVY};font-weight:bold;margin:12px 0;">{esc(s)}</p>'
    def small(s): return f'<p style="font-size:12px;color:#52606a;margin:16px 0 0;">{paragraphs(s)}</p>'
    rows=block(f'<table role="presentation" align="center" width="165"><tr><td>{image("logo","Casa Dorada",165)}</td></tr></table>',padding='18px')
    if d['ai']:
        rows+=block(image('pool','Relax and enjoy your stay at Casa Dorada'),padding='0')
    rows+=block('<p style="font-size:11px;letter-spacing:2px;color:#806841;margin:0 0 8px;">YOUR VACATION STARTS HERE</p>'+heading(d['headline'])+f'<p style="margin:8px 0;">Dear {esc(d["name"] or "Guest")}, {paragraphs(d["intro"])}</p>'+ (small('Reservation: '+d['reservation']+' | Arrival: '+d['arrival']) if d['reservation'] or d['arrival'] else ''),SAND,'22px 28px')
    if d['ai']:
        benefits=[v.strip() for v in d['ai_benefits'].splitlines() if v.strip()]
        cards=[]
        for v in benefits:
            title,sep,desc=v.partition('|')
            if not sep: title,desc=v,''
            cards.append(f'<td class="benefit" width="50%" valign="top" bgcolor="{SAND}" style="padding:14px;text-align:center;"><strong style="font-family:Georgia,serif;font-size:{24 if "%" in title else 18}px;color:{NAVY};">{esc(title.strip())}</strong><p style="font-size:13px;line-height:1.5;margin:6px 0 0;">{esc(desc.strip())}</p></td>')
        benefit_html=('<p style="font-size:11px;letter-spacing:2px;color:#806841;margin:24px 0 8px;">MORE THAN JUST A MEAL PLAN</p>'+heading('Discover your All-Inclusive privileges')+'<table role="presentation" width="100%" cellspacing="6" cellpadding="0">'+''.join('<tr>'+''.join(cards[i:i+2])+('<td></td>' if i+1==len(cards) else '')+'</tr>' for i in range(0,len(cards),2))+'</table>') if cards else ''
        rows+=block('<p style="font-size:11px;letter-spacing:3px;color:#806841;margin:0;">DINE &nbsp;·&nbsp; RELAX &nbsp;·&nbsp; ENJOY</p>'+f'<h1 style="font:normal 36px/1.15 Georgia,serif;color:{NAVY};margin:12px 0;">{esc(d["ai_title"])}</h1><p>{paragraphs(d["ai_desc"])}</p>'+benefit_html+f'<p style="font:normal 44px/1.1 Georgia,serif;color:{NAVY};margin:24px 0 4px;">${d["ai_price"]:,.2f} <span style="font-size:18px;">USD</span></p><p style="font-size:14px;margin:0 0 20px;">Per adult, per night</p>'+cta(d['ai_button'],'All-Inclusive')+small(d['ai_terms']),padding='32px 28px')
        if d['gallery']:
            rows+=block('<table role="presentation" width="100%" cellspacing="4"><tr>'+''.join(f'<td width="33%" valign="middle">{image(k,a,180)}</td>' for k,a in [('burger','Burger'),('pizza','Pizza'),('dining','Dining')])+'</tr></table>',padding='0 14px 24px')
        if d['ai']:
            thumb=f'<td width="112" valign="middle" style="padding-right:14px;">{image("transport","Private transportation",100)}</td>' if d['tr_photo'] else ''
            detail=f'<p style="font-size:11px;letter-spacing:1.5px;color:#806841;margin:0 0 5px;">ALSO AVAILABLE</p><h2 style="font:normal 21px Georgia,serif;color:{NAVY};margin:0 0 8px;">{esc(d["tr_title"])}</h2><p style="font-size:13px;line-height:1.5;margin:0 0 8px;">{paragraphs(d["tr_desc"])}</p><p style="font-size:14px;line-height:1.5;margin:0;"><strong>One way:</strong> from {money(d["one"])}<br><strong>Round trip:</strong> {money(d["round"])}</p>'
            detail+=cta(d['tr_button'],'Private Transportation',True)+small(d['tr_terms'])
            rows+=block(f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>{thumb}<td valign="middle" style="text-align:left;">{detail}</td></tr></table>',SAND,'20px')
        else:
            if d['tr_photo']: rows+=block(image('transport','Private transportation'),padding='0')
            rows+=block(heading(d['tr_title'])+f'<p>{paragraphs(d["tr_desc"])}</p><p>One way: from <strong>{money(d["one"])}</strong><br>Round trip: <strong>{money(d["round"])}</strong></p>'+ cta(d['tr_button'],'Private Transportation')+small(d['tr_terms']),SAND)
    rows+=f'<tr><td bgcolor="{NAVY}" style="padding:26px;text-align:center;font:15px Arial,sans-serif;color:#ffffff;line-height:1.6;">We look forward to welcoming you.<br><strong>Casa Dorada Reservations Team</strong><br><a style="color:#ffffff;" href="mailto:{esc(d["email"])}">{esc(d["email"])}</a></td></tr>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(d['subject'])+'</title><style>@media only screen and (max-width:480px){.benefit{display:block!important;width:auto!important;margin-bottom:6px;}}</style></head><body style="margin:0;padding:0;background:#eef0f2;"><div style="display:none;max-height:0;max-width:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;">'+esc(d['preheader'])+'</div><table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#eef0f2"><tr><td align="center"><table role="presentation" width="600" cellspacing="0" cellpadding="0" bgcolor="#ffffff" style="width:100%;max-width:600px;margin:auto;">'+rows+'</table></td></tr></table></body></html>',used

st.title('Casa Dorada · Email Studio')
st.caption('Generador de correos Pre-Arrival | All Inclusive protagonista')
with st.sidebar:
    st.header('Configuración')
    ai=st.checkbox('All Inclusive',True); tr=st.checkbox('Transportación',True)
    gallery=st.checkbox('Galería gastronómica',True)
    tr_photo=st.checkbox('Foto pequeña de transportación',True)
    email=st.text_input('Correo de contacto','reservations@casadorada.com')
    st.caption('Los botones abren un correo dirigido a reservaciones; no generan solicitudes ni cobran automáticamente.')
left,right=st.columns([1,1.15])
with left:
    st.subheader('Personalizar correo')
    with st.expander('Huésped y encabezado',expanded=True):
        name=st.text_input('Nombre del huésped'); reservation=st.text_input('Número de confirmación'); arrival=st.text_input('Llegada (texto opcional)')
        subject=st.text_input('Asunto','Discover the All-Inclusive experience at Casa Dorada' if ai else 'Arrange your airport transportation at Casa Dorada')
        recipient=st.text_input('Correo del huésped')
        personalize=st.checkbox('Personalizar asunto con nombre',True)
        if personalize and name.strip(): subject=name.strip().split()[0]+', '+subject
        preheader=st.text_input('Preheader','Discover our All-Inclusive experience and exclusive spa privileges.' if ai else 'Arrange your private airport transfer before arrival.',max_chars=150)
        headline=st.text_input('Título','More moments in paradise')
        intro=st.text_area('Introducción','We look forward to welcoming you. Discover how our All-Inclusive meal plan can enhance your upcoming stay.' if ai else 'We look forward to welcoming you. Arrange your airport transfer before arrival.')
    with st.expander('All Inclusive',expanded=ai):
        ai_title=st.text_input('Título All Inclusive','All-Inclusive in Paradise')
        ai_desc=st.text_area('Descripción All Inclusive','Enjoy your favorite meals, sip a refreshing cocktail by the pool, and make the most of your vacation with our All-Inclusive plan.')
        defaults=['Domestic Bar | Full domestic bar service at all resort bars, from 7:00 AM to 11:00 PM.', 'Daily Mini-Bar | 8 sodas, 4 bottles of water, 6 domestic beers and 2 coffee kits daily.', '30% OFF | Room Service', '20% OFF | Saltwater Spa', 'Complimentary Wellness Access | Free access to our gym and Saltwater Spa wet areas.']
        selected=[]
        for i,benefit in enumerate(defaults):
            if st.checkbox('Incluir '+benefit.split('|')[0].strip(),True,key=f'benefit_on_{i}'):
                selected.append(st.text_input('Beneficio '+str(i+1),benefit,key=f'benefit_text_{i}'))
        ai_benefits='\n'.join(selected)
        ai_price=st.number_input('USD por adulto por noche',min_value=0.0,value=149.0,step=1.0)
        ai_terms=st.text_area('Condiciones All Inclusive','Additional to your room rate. Terms and restrictions apply.')
        ai_button=st.text_input('Botón All Inclusive','Request All-Inclusive')
    with st.expander('Transportación',expanded=tr):
        tr_title=st.text_input('Título transporte','Private Airport Transportation')
        tr_desc=st.text_area('Descripción transporte','Arrange your private airport transfer before arrival.')
        one=st.number_input('One way desde USD',min_value=0.0,value=149.0,step=1.0)
        round_price=st.number_input('Round trip USD',min_value=0.0,value=267.0,step=1.0)
        tr_terms=st.text_area('Condiciones transporte','Up to 5 passengers. Advance booking of at least 72 hours required.')
        tr_button=st.text_input('Botón transporte','Request transportation')
    images={}
    with st.expander('Fotografías y logo'):
        st.caption('Usa las fotos originales incluidas, sube una nueva o indica una URL HTTPS pública. La URL tiene prioridad.')
        for k,label in [('logo','Logo'),('pool','All Inclusive / piscina'),('burger','Galería 1'),('pizza','Galería 2'),('dining','Galería 3'),('transport','Transportación')]:
            up=st.file_uploader(label,type=['jpg','jpeg','png','webp'],key='up_'+k)
            url=st.text_input('URL HTTPS · '+label,key='url_'+k)
            images[k]=get_image(k,up,url)
    d=dict(preheader=preheader,ai=ai,transport=tr,gallery=gallery,tr_photo=tr_photo,ai_benefits=ai_benefits,email=email,name=name,reservation=reservation,arrival=arrival,subject=subject,headline=headline,intro=intro,ai_title=ai_title,ai_desc=ai_desc,ai_price=ai_price,ai_terms=ai_terms,ai_button=ai_button,tr_title=tr_title,tr_desc=tr_desc,one=one,round=round_price,tr_terms=tr_terms,tr_button=tr_button)
    valid=bool(re.fullmatch(r'[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+',email)) and '\n' not in subject and '\r' not in subject
    if not valid: st.error('Revisa el correo de contacto y el asunto.')
    if not (ai or tr): st.warning('Selecciona al menos un servicio.')
    ready=valid and (ai or tr)
    page,used=build(d,images)
    # Optimize only the images actually used, including original assets.
    for k in used:
        if images[k][0]=='bytes':
            im=Image.open(BytesIO(images[k][1])).convert('RGB')
            im.thumbnail((1000 if k=='pool' else 500,1000 if k=='pool' else 500))
            for quality in (85,75,65,55,45):
                b=BytesIO(); im.save(b,format='JPEG',quality=quality,optimize=True)
                if b.tell()<= (180000 if k=='pool' else 60000): break
            images[k]=('bytes',b.getvalue())
    embedded_size=sum(len(images[k][1]) for k in used if images[k][0]=='bytes')
    st.metric('Peso de imágenes incrustadas',f'{embedded_size/1024:.1f} KB')
    if embedded_size>500*1024: st.warning('Las imágenes superan 500 KB.')
    if any(images[k][0]=='url' for k in used): st.caption('El peso de imágenes externas no está incluido.')
    page,used=build(d,images)
    st.download_button('Descargar HTML',page,file_name='Casa_Dorada_PreArrival.html',mime='text/html',disabled=not ready)
    if ready:
        eml,used=build(d,images,'eml'); msg=EmailMessage(policy=policy.SMTP); msg['Subject']=subject
        recipient_valid=bool(re.fullmatch(r'[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+',recipient))
        if recipient_valid: msg['To']=recipient
        if gmail_email: msg['From']=formataddr(('Casa Dorada Reservations',gmail_email))
        plain=[preheader,'Dear '+(name or 'Guest')+',',intro,'Reservation: '+reservation,'Arrival: '+arrival]
        if ai: plain.extend([ai_title,ai_desc,ai_benefits.replace(' | ',': '),money(ai_price)+' per adult, per night',ai_terms])
        if tr: plain.extend([tr_title,tr_desc,'One way: from '+money(one),'Round trip: '+money(round_price),tr_terms])
        plain.extend(['To request services, contact '+email,'Casa Dorada Reservations Team'])
        msg.set_content('\n\n'.join(plain)); msg.add_alternative(eml,subtype='html'); part=msg.get_payload()[-1]
        for k in sorted(used):
            if images[k][0]=='bytes': part.add_related(images[k][1],maintype='image',subtype='jpeg',cid='<'+k+'@casadorada.local>')
        st.download_button('Descargar correo .eml',msg.as_bytes(),file_name='Casa_Dorada_PreArrival.eml',mime='message/rfc822')
        if st.button('Crear borrador en Gmail',disabled=not (gmail_email and recipient_valid),type='primary'):
            try:
                result=create_draft(msg)
                st.success('Borrador creado en Gmail. Revisa y envía desde tu cuenta.')
            except Exception:
                st.error('No se pudo crear el borrador. Revisa la conexión con Gmail antes de reintentar.')
        if not recipient_valid: st.caption('Introduce un correo válido del huésped para crear el borrador.')
    st.caption('HTML: abre en navegador y copia el contenido visual a Gmail. Gmail puede eliminar imágenes incrustadas; para ese flujo usa URLs públicas HTTPS autorizadas y verifica con un correo de prueba. EML: para clientes compatibles, no se importa directamente como borrador en Gmail.')
with right:
    st.subheader('Vista previa')
    device=st.radio('Pantalla',['Escritorio','Móvil'],horizontal=True)
    components.html('<div style="margin:auto;max-width:'+('375px' if device=='Móvil' else '600px')+'">'+page+'</div>',height=1550,scrolling=True)
    with st.expander('Código HTML'): st.code(page,language='html')
