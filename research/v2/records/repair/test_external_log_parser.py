from external_log_taxonomy import signals
cases = [
 ('1 failed, 4 passed in 1s\nFAILED tests/test_a.py::test_x - AssertionError: 1 != 2','assertion_summary_only',True),
 ('1 failed, 1 error in 1s\nFAILED tests/test_a.py::test_x - AssertionError\nERROR tests/test_a.py::test_b','assertion_summary_only',False),
 ('1 failed in 1s\nFAILED tests/test_a.py::test_x - ValueError: bad','assertion_summary_only',False),
 ('collected 1 items / 1 error\nERROR tests/test_import.py','assertion_summary_only',False),
 ('collected 1 items','successful_test_summary',False),
 ('Ran 8 tests in 1s\nOK','successful_test_summary',True),
 ('AssertionError: fail\nFAILED (failures=1)','assertion_summary_only',True),
 ('AssertionError: fail\nFAILED (failures=1, errors=1)','assertion_summary_only',False),
]
for text,field,expected in cases:assert signals(text)[field] == expected
print('8 parser edge-case checks passed')
