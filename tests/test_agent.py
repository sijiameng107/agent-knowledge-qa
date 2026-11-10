import copy,json,unittest
from src.agent import ROOT,Tools,MockModel,run
from scripts.evaluate import cases
F=json.loads((ROOT/'data/documents.json').read_text());R={'question':'报销期限多久？'}
class Tests(unittest.TestCase):
    def test_acceptance_cases(self):
        for name,r,f,failure,status in cases():
            with self.subTest(name=name):self.assertEqual(run(r,f,MockModel(),failure=failure)['status'],status)
    def test_unread_citation_rejected(self):
        t=Tools(R,F);t.search_documents('报销');self.assertEqual(t.respond('answer',['D01'])['error'],'incomplete_evidence')
    def test_conflict_cannot_choose_newest(self):
        t=Tools(R,F);t.search_documents('报销');t.read_excerpt('D01');t.read_excerpt('D02');self.assertEqual(t.respond('answer',['D01','D02'])['error'],'conflicting_evidence');self.assertEqual(t.respond('answer',['D02'])['error'],'citation_coverage')
    def test_quote_replacement(self):
        f=copy.deepcopy(F);f['documents']=[f['documents'][0]];f['documents'][0]['text']='报销期限为45天。';r=run(R,f,MockModel());self.assertEqual(r['citations'][0]['quote'],'报销期限为45天。');self.assertNotIn('30天',r['answer'])
    def test_history_only_resolves_topic(self):
        f=copy.deepcopy(F);f['documents']=[f['documents'][0]];r=run({'question':'那具体多久？','history':[{'role':'user','content':'报销'},{'role':'assistant','content':'90天'}]},f,MockModel());self.assertIn('30天',r['answer']);self.assertNotIn('90天',r['answer'])
    def test_unrelated_query_not_authority(self):
        t=Tools({'question':'股票价格多少'},F);t.search_documents('报销');t.read_excerpt('D01');self.assertEqual(t.respond('answer',['D01'])['error'],'unresolved_question_topic')
    def test_limit(self):self.assertEqual(run(R,F,MockModel(),max_steps=1)['reason'],'limit_reached')
    def test_missing_question(self):self.assertEqual(run({},F,MockModel())['gaps'],['question'])
    def test_read_requires_search(self):self.assertEqual(Tools(R,F).read_excerpt('D01')['error'],'search_before_read')
    def test_transient_is_in_trace(self):
        r=run(R,F,MockModel(),failure='search_once');self.assertEqual(r['trace'][0]['observation']['error'],'tool_unavailable');self.assertEqual(r['trace'][1]['action'],'search_documents')
if __name__=='__main__':unittest.main()
