"""Record locked dependencies and installed upstream notice texts; never infer legal approval."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def inventory(root=ROOT):
    ui=root/'frontend/owner-ui'
    lock_bytes=(ui/'package-lock.json').read_bytes()
    lock=json.loads(lock_bytes)
    components=[];texts=[]
    supplements=json.loads((root/'docs/OWNER_UI_UPSTREAM_NOTICES.json').read_text())['entries']
    for location,row in sorted(lock['packages'].items()):
        if not location:continue
        parts=Path(location).parts
        if Path(location).is_absolute() or '..' in parts or parts[0]!='node_modules':raise ValueError('unsafe dependency path')
        directory=ui/location
        if directory.is_symlink() or any(p.is_symlink() for p in directory.parents):raise ValueError('symlink dependency')
        installed=(directory/'package.json').is_file()
        package=json.loads((directory/'package.json').read_text()) if installed else {}
        if installed and package.get('version')!=row['version']:raise ValueError('installed dependency differs from lock')
        notices=[]
        if installed:
            for p in sorted(directory.iterdir()):
                if not p.name.lower().startswith(('license','licence','notice','copying','copyright')):continue
                if p.is_symlink():raise ValueError('symlink notice')
                if not p.is_file():continue
                raw=p.read_bytes();content=raw.decode('utf-8')
                notices.append({'file':p.name,'sha256':hashlib.sha256(raw).hexdigest()})
                texts.append(f'\n===== {location} @ {row["version"]} / {p.name} =====\n'+content+'\n')
        supplemental=next((x for x in supplements if x['name']==package.get('name') and x['version']==row['version']),None)
        if not notices and supplemental:
            raw=supplemental['text'].encode('utf-8')
            if hashlib.sha256(raw).hexdigest()!=supplemental['sha256']:raise ValueError('upstream notice changed')
            notices.append({'file':'upstream/LICENSE','sha256':supplemental['sha256'],'url':supplemental['url'],'version_link_evidence':supplemental['version_link_evidence']})
            texts.append(f"\n===== {location} @ {row['version']} / upstream LICENSE =====\nSource: {supplemental['url']}\n"+supplemental['text']+'\n')
        components.append({'lock_path':location,'name':package.get('name') or location.rsplit('node_modules/',1)[-1],
                           'version':row['version'],'resolved':row.get('resolved'),'integrity':row.get('integrity'),
                           'development_only_declared':row.get('dev',False),'optional_declared':row.get('optional',False),
                           'license_declared':package.get('license',row.get('license')),'installed_for_this_inventory':installed,
                           'notice_files':notices,'notice_status':'upstream_text_recorded' if notices else 'not_installed_platform_optional' if not installed and row.get('optional') else 'missing_upstream_text_requires_review'})
    result={'format':'awesome-owner-ui-dependencies-v1','lock_sha256':hashlib.sha256(lock_bytes).hexdigest(),
            'scope':'Full lock graph; installed package root notices. Not a claim that every dependency is in browser chunks. Other-platform optional packages are not installed or vendored.',
            'legal_approved':False,'public_release_approved':False,'components':components}
    output=root/'docs'
    (output/'OWNER_UI_DEPENDENCIES.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (output/'OWNER_UI_THIRD_PARTY_LICENSES.txt').write_text('Upstream notice texts from installed locked dependencies. Technical collection; missing texts are listed in OWNER_UI_DEPENDENCIES.json. Not the project license or legal approval.\n'+''.join(texts))
    return result

if __name__=='__main__':
    result=inventory()
    print(json.dumps({'components':len(result['components']),'recorded':sum(bool(x['notice_files']) for x in result['components']),'missing':[x['name'] for x in result['components'] if x['notice_status']=='missing_upstream_text_requires_review']}))
