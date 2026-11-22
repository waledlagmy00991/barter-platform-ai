"""Fixed-query compatibility check. This is not model task evaluation."""
import json,os,sys,resource
from pathlib import Path
from chatbot.chatbot import search
queries=[
 'عايز ٥ طن حديد تسليح جديد في القاهرة','حديد خردة هالك في العاشر',
 'نحاس مستعمل في المنصورة','خشب زان جديد في القاهرة','خشب سويد جديد في دمياط',
 'ألومنيوم مستعمل طن','بلاستيك مجروش مستعمل في شبرا','أسمنت جديد في القاهرة',
 'MDF ألواح جديد','رمل جديد متر مكعب','زلط في الاسكندرية','طوب أحمر في الجيزة',
]
rows=[]
for q in queries:
 matches=search(q,k=3)
 rows.append({'query':q,'top3':[r['id'] for r in matches],'scores':[r['score'] for r in matches]})
result={'purpose':'Fixed query deployment compatibility, not unseen accuracy or readiness','backend':os.getenv('BARTER_EMBEDDING_BACKEND','sentence_transformers'),'rows':rows,'maxrss_mb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
Path(sys.argv[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('Compatibility outputs saved; max RSS MB:',result['maxrss_mb'])
