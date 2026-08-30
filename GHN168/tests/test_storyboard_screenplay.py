import os
import unittest

class TestStoryboardScreenplay(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(self.base_dir, "assets")

    def test_master_hub_screenplay_section(self):
        master_path = os.path.join(self.assets_dir, "ghn168_storyboard_master.html")
        self.assertTrue(os.path.exists(master_path), "Master storyboard hub must exist")

        with open(master_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check section & typography
        self.assertIn("screenplay-section", content)
        self.assertIn("Official Production Screenplay", content)
        self.assertIn("Courier Prime", content)

        # Check all 5 characters
        characters = [
            "THE CLIENT",
            "KENG",
            "NICK",
            "HOM",
            "MOD"
        ]
        for char in characters:
            self.assertIn(char, content, f"Character {char} should be present in master screenplay")

        # Check 3 versions content
        self.assertIn("sp-content-v1", content)
        self.assertIn("sp-content-v2", content)
        self.assertIn("sp-content-v3", content)

        # Check V1 key dialogues
        self.assertIn("DRAFT_1_PUAD-HUAD", content)
        self.assertIn("งานเนียนไป!! เนี้ยบเกินไปจนไม่มีมิติ", content)
        self.assertIn("คนจ่ายเงินอย่างชั้น ถ้าไม่ได้กดสั่งแก้ดราฟต์งาน", content)

        # Check V2 key dialogues
        self.assertIn("เมตตาคนอย่างชั้นด้วยเถอะ", content)
        self.assertIn("ทำไมต้องตัดต่อออกมาดีขนาดนี้ด้วย", content)
        self.assertIn("ในที่สุด... ชาตินี้ชั้นก็ได้กดสั่งแก้สมใจแล้ว", content)

        # Check V3 key dialogues & Post-Credit
        self.assertIn("TALKING HEAD INTERVIEW", content)
        self.assertIn("EDIT COUNT", content)
        self.assertIn("POST-CREDIT SCENE", content)
        self.assertIn("ขอถอยกลับไปเอา 'ดราฟต์แรกสุด' เลยได้ไหมครับ", content)

    def test_v1_thriller_storyboard_3_pages(self):
        v1_path = os.path.join(self.assets_dir, "ghn168_storyboard_v1_thriller.html")
        self.assertTrue(os.path.exists(v1_path), "V1 storyboard HTML must exist")

        with open(v1_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check 3 pages headers & footers
        self.assertIn("PAGE 1 OF 3", content)
        self.assertIn("PAGE 2 OF 3", content)
        self.assertIn("PAGE 3 OF 3", content)
        self.assertIn("PAGE 1 / 3", content)
        self.assertIn("PAGE 2 / 3", content)
        self.assertIn("PAGE 3 / 3", content)

        # Check Page 3 Title & Elements
        self.assertIn("Production Screenplay & Actor Dialogue Sheet", content)
        self.assertIn("screenplay-sheet", content)
        self.assertIn("script-card", content)
        self.assertIn("script-action-box", content)

        # Check shots
        self.assertIn("SHOT 1A", content)
        self.assertIn("SHOT 1B", content)
        self.assertIn("SHOT 2A", content)
        self.assertIn("SHOT 2B", content)
        self.assertIn("DRAFT 1 PUAD-HUAD", content)

        # Check dialogues & cues
        self.assertIn("THE CLIENT (ลูกค้า)", content)
        self.assertIn("KENG (พี่เก่ง)", content)
        self.assertIn("NICK (พี่นิค)", content)
        self.assertIn("HOM (พี่หอม)", content)
        self.assertIn("MOD (บอสมด)", content)
        self.assertIn("พวกคุณ... รู้ตัวไหมว่าทำอะไรลงไป?", content)
        self.assertIn("งานเนียนไป!! เนี้ยบเกินไปจนไม่มีมิติ", content)
        self.assertIn("รหัสลับ โอเมก้า วัน วัน หก แปด", content)

        # Check print css rules
        self.assertIn("@media print", content)
        self.assertIn("page-break-after: always;", content)
        self.assertIn("break-after: page;", content)

    def test_v2_soapopera_storyboard_3_pages(self):
        v2_path = os.path.join(self.assets_dir, "ghn168_storyboard_v2_soapopera.html")
        self.assertTrue(os.path.exists(v2_path), "V2 storyboard HTML must exist")

        with open(v2_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check 3 pages headers & footers
        self.assertIn("PAGE 1 OF 3", content)
        self.assertIn("PAGE 2 OF 3", content)
        self.assertIn("PAGE 3 OF 3", content)
        self.assertIn("PAGE 1 / 3", content)
        self.assertIn("PAGE 2 / 3", content)
        self.assertIn("PAGE 3 / 3", content)

        # Check Page 3 Title & Elements
        self.assertIn("Production Screenplay & Actor Dialogue Sheet", content)
        self.assertIn("screenplay-sheet", content)
        self.assertIn("script-card", content)

        # Check shots
        self.assertIn("SHOT 1A", content)
        self.assertIn("SHOT 1B", content)
        self.assertIn("SHOT 2A", content)
        self.assertIn("SHOT 2B", content)

        # Check dialogues & emotional directions
        self.assertIn("THE CLIENT (ลูกค้า)", content)
        self.assertIn("เมตตาคนอย่างชั้นด้วยเถอะ", content)
        self.assertIn("ทำไมต้องตัดต่อออกมาดีขนาดนี้ด้วย", content)
        self.assertIn("ดราฟต์ที่ 1 ที่เราแอบทำเละไว้", content)
        self.assertIn("ในที่สุด... ชาตินี้ชั้นก็ได้กดสั่งแก้สมใจแล้ว", content)

        # Check print css rules
        self.assertIn("@media print", content)
        self.assertIn("page-break-after: always;", content)
        self.assertIn("break-after: page;", content)

    def test_v3_mockumentary_storyboard_3_pages(self):
        v3_path = os.path.join(self.assets_dir, "ghn168_storyboard_v3_mockumentary.html")
        self.assertTrue(os.path.exists(v3_path), "V3 storyboard HTML must exist")

        with open(v3_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check 3 pages headers & footers
        self.assertIn("PAGE 1 OF 3", content)
        self.assertIn("PAGE 2 OF 3", content)
        self.assertIn("PAGE 3 OF 3", content)
        self.assertIn("PAGE 1 / 3", content)
        self.assertIn("PAGE 2 / 3", content)
        self.assertIn("PAGE 3 / 3", content)

        # Check Page 3 Title & Elements
        self.assertIn("Production Screenplay & Actor Dialogue Sheet", content)
        self.assertIn("screenplay-sheet", content)
        self.assertIn("script-card", content)

        # Check shots
        self.assertIn("SHOT 1A", content)
        self.assertIn("SHOT 1B", content)
        self.assertIn("SHOT 2A", content)
        self.assertIn("SHOT 2B", content)

        # Check mockumentary elements & Post-Credit
        self.assertIn("TALKING HEAD", content)
        self.assertIn("EDIT COUNT", content)
        self.assertIn("POST-CREDIT", content)
        self.assertIn("ความมินิมอลครับ", content)
        self.assertIn("ขอถอยกลับไปเอา 'ดราฟต์แรกสุด' เลยได้ไหมครับ", content)
        self.assertIn("...ฮู่ววววว์!", content)

        # Check print css rules
        self.assertIn("@media print", content)
        self.assertIn("page-break-after: always;", content)
        self.assertIn("break-after: page;", content)

if __name__ == "__main__":
    unittest.main()

