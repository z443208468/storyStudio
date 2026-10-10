import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import cnw_lint, cnw_review

class ReviewTests(unittest.TestCase):
    def test_lints_report_line_evidence_without_editing(self):
        text="第一行\n她感到悲伤。\nTODO 待补充  \n"
        before=text
        a=cnw_lint.lint(text,"surface"); b=cnw_lint.lint(text,"structural")
        self.assertEqual(text,before); self.assertFalse(a["text_modified"])
        self.assertTrue(any(x["rule_id"]=="PLACEHOLDER" and x["line"]==3 for x in a["findings"]))
        self.assertTrue(any(x["rule_id"]=="ABSTRACT_EMOTION" and x["line"]==2 for x in b["findings"]))
        self.assertTrue(all(x["disposition"]=="CANDIDATE_ONLY" for x in b["findings"]))
    def test_five_lenses_are_isolated_and_mock_only(self):
        sources={"style_guide":"STYLE","character_bible":"CHAR","plot":"PLOT","canon":"CANON","story_contract":"CANGQI"}
        result=cnw_review.review_offline("她推开门。",sources)
        lenses=result["lenses"]
        self.assertEqual({x["lens_id"] for x in lenses},set(cnw_review.LENSES))
        self.assertEqual(len({x["input_sha256"] for x in lenses}),5)
        self.assertEqual(len({x["simulated_output"]["scope"] for x in lenses}),5)
        self.assertEqual(lenses[0]["input_packet"]["sources"],{"style_guide":"STYLE"})
        self.assertEqual(lenses[1]["input_packet"]["sources"],{"character_bible":"CHAR"})
        self.assertTrue(all(x["provider_request_id"] is None and x["execution_mode"]=="MOCK_ONLY" for x in lenses))
        self.assertEqual(result["provider_request_ids"],[])
        self.assertFalse(result["text_modified"])
    def test_verifier_default_uncertain_does_not_confirm_and_two_votes_do(self):
        findings=[{"finding_id":"f1"}]
        packets=cnw_review.verifier_packets(findings,"draft")
        self.assertEqual(len({x["input_sha256"] for x in packets}),3)
        votes=[{**p,"votes":[{"finding_id":"f1","verdict":v}]} for p,v in zip(packets,["not_refuted","uncertain","refuted"])]
        self.assertEqual(cnw_review.tally_verifiers(votes)["f1"]["status"],"REFUTED_OR_UNCERTAIN")
        votes[1]["votes"][0]["verdict"]="not_refuted"
        self.assertEqual(cnw_review.tally_verifiers(votes)["f1"]["status"],"CONFIRMED")
    def test_verifier_packets_are_inspectable_and_vote_once(self):
        findings=[{"finding_id":"f1"}]; sources={"canon":"source evidence"}
        packets=cnw_review.verifier_packets(findings,"complete scene",sources)
        self.assertTrue(all(p["draft"]=="complete scene" and p["findings"]==findings and p["sources"]==sources for p in packets))
        self.assertEqual(len({p["input_sha256"] for p in packets}),3)
        malicious=[]
        for p in packets:
            malicious.append({**p,"votes":[{"finding_id":"f1","verdict":"not_refuted"},{"finding_id":"f1","verdict":"not_refuted"}]})
        with self.assertRaisesRegex(ValueError,"duplicate vote"):
            cnw_review.tally_verifiers(malicious)
    def test_mock_cannot_claim_real_request_id(self):
        packets=cnw_review.verifier_packets([],"draft")
        packets[0]["provider_request_id"]="fake-live-id"
        with self.assertRaises(ValueError): cnw_review.tally_verifiers(packets)
    def test_completeness_reads_full_text_and_prior_dispositions(self):
        p=cnw_review.completeness_packet("full scene text",[{"id":"confirmed"}],[{"id":"rejected"}],{"canon":"source"})
        self.assertEqual(p["draft"],"full scene text")
        self.assertEqual(p["confirmed_findings"][0]["id"],"confirmed")
        self.assertEqual(p["rejected_findings"][0]["id"],"rejected")
        self.assertEqual(p["provider_request_id"],None)
        self.assertEqual(p["sources"],{"canon":"source"})
    def test_completeness_receives_only_vote_dispositions_and_hashes_all_fields(self):
        result=cnw_review.review_offline("TODO\nfull prose",{"canon":"canon material"})
        packet=result["completeness"]
        self.assertEqual(packet["confirmed_findings"],[])
        self.assertTrue(all(x["verifier_votes"]==["uncertain"]*3 for x in packet["rejected_findings"]))
        self.assertEqual(packet["sources"],{"canon":"canon material"})
        self.assertIn("full prose",packet["draft"])
        self.assertEqual(packet["input_sha256"],cnw_review.digest(__import__("json").dumps({k:v for k,v in packet.items() if k!="input_sha256"},ensure_ascii=False,sort_keys=True)))

if __name__=="__main__": unittest.main()
