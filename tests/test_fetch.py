# Copyright (C) 2007 Jelmer Vernooij <jelmer@samba.org>
# *-* coding: utf-8 *-*

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Subversion fetch tests."""

import shutil
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.osutils import has_symlinks
from bzrlib.repository import Repository
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import TestSkipped, KnownFailure
from bzrlib.trace import mutter

from bzrlib.plugins.svn import format, remote
from bzrlib.plugins.svn.convert import load_dumpfile
from bzrlib.plugins.svn.errors import InvalidFileName
from bzrlib.plugins.svn.mapping3 import set_branching_scheme
from bzrlib.plugins.svn.mapping3.scheme import TrunkBranchingScheme, NoBranchingScheme
from bzrlib.plugins.svn.tests import TestCaseWithSubversionRepository
from bzrlib.plugins.svn.transport import SvnRaTransport

import os, sys

class TestFetchWorks(TestCaseWithSubversionRepository):
    def test_fetch_fileid_renames(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_file("test", "data")
        dc.change_dir_prop("", "bzr:file-ids", "test\tbla\n")
        dc.change_dir_prop("", "bzr:revision-info", "")
        dc.done()

        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertEqual("bla", newrepos.get_inventory(
            oldrepos.generate_revision_id(1, "", mapping)).path2id("test"))

    def test_fetch_trunk1(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("proj1")
        dc.add_dir("proj1/trunk")
        dc.add_file("proj1/trunk/file", "data")
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(1))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_replace_from_branch(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_dir("trunk/check")
        dc.add_dir("trunk/check/debian")
        dc.add_file("trunk/check/stamp-h.in", "foo")
        dc.add_dir("tags")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_file("trunk/check/debian/pl", "bar")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_file("trunk/check/debian/voo", "bar")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_file("trunk/check/debian/blie", "oeh")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_file("trunk/check/debian/bar", "oeh")
        dc.add_file("trunk/check/bar", "bla")
        dc.done()

        self.make_checkout(repos_url, "dc")

        self.client_copy("dc/trunk", "dc/tags/R_0_9_2", revnum=2)
        self.client_delete("dc/tags/R_0_9_2/check/debian")
        shutil.rmtree("dc/tags/R_0_9_2/check/debian")
        self.client_copy("dc/trunk/check/debian", "dc/tags/R_0_9_2/check", 
                         revnum=5)
        self.client_delete("dc/tags/R_0_9_2/check/stamp-h.in")
        self.client_copy("dc/trunk/check/stamp-h.in", "dc/tags/R_0_9_2/check", 
                         revnum=4)
        self.build_tree({"dc/tags/R_0_9_2/check/debian/blie": "oehha"})
        self.client_update("dc")
        self.client_commit("dc", "strange revision")
        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(0))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_backslash(self):
        if sys.platform == 'win32':
            raise TestSkipped("Unable to create filenames with backslash on Windows")
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file("trunk/file\\part", "data")
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        self.assertRaises(InvalidFileName, oldrepos.copy_content_into, newrepos)

    def test_fetch_null(self):
        repos_url = self.make_repository('d')
        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(1))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos, NULL_REVISION)

    def test_fetch_complex_ids_dirs(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("dir")
        dc.add_dir("dir/adir")
        dc.change_dir_prop("", "bzr:revision-info", "")
        dc.change_dir_prop("", "bzr:file-ids", "dir\tbloe\ndir/adir\tbla\n")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_dir("bdir", "dir/adir")
        dc.delete("dir/adir")
        dc.change_dir_prop("", "bzr:revision-info", "properties: \n")
        dc.change_dir_prop("", "bzr:file-ids", "bdir\tbla\n")
        dc.done()

        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        tree = newrepos.revision_tree(oldrepos.generate_revision_id(2, "", mapping))
        self.assertEquals("bloe", tree.path2id("dir"))
        self.assertIs(None, tree.path2id("dir/adir"))
        self.assertEquals("bla", tree.path2id("bdir"))

    def test_fetch_complex_ids_files(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/dir/adir': 'contents'})
        self.client_add("dc/dir")
        self.client_set_prop("dc", "bzr:revision-info", "")
        self.client_set_prop("dc", "bzr:file-ids", "dir\tbloe\ndir/adir\tbla\n")
        self.client_commit("dc", "My Message")
        self.client_update("dc")
        self.client_copy("dc/dir/adir", "dc/bdir")
        self.client_delete("dc/dir/adir")
        self.client_set_prop("dc", "bzr:revision-info", "properties: \n")
        self.client_set_prop("dc", "bzr:file-ids", "bdir\tbla\n")
        self.client_commit("dc", "My Message")
        self.client_update("dc")
        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        tree = newrepos.revision_tree(oldrepos.generate_revision_id(2, "", mapping))
        self.assertEquals("bloe", tree.path2id("dir"))
        self.assertIs(None, tree.path2id("dir/adir"))
        mutter('entries: %r' % tree.inventory.entries())
        self.assertEquals("bla", tree.path2id("bdir"))

    def test_fetch_copy_remove_old(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/trunk/afile': 'foo', 'dc/tags': None, 
                         'dc/branches': None})
        self.client_add("dc/trunk")
        self.client_add("dc/tags")
        self.client_add("dc/branches")
        self.client_commit("dc", "My Message")
        self.client_update("dc")
        self.client_copy("dc/trunk", "dc/branches/blal")
        self.build_tree({'dc/branches/blal/afile': "bar"})
        self.client_commit("dc", "Msg")
        self.client_update("dc")
        self.client_copy("dc/trunk", "dc/tags/bla")
        self.client_delete("dc/tags/bla/afile")
        self.client_copy("dc/branches/blal/afile", "dc/tags/bla/afile")
        self.client_commit("dc", "My Message")
        self.client_update("dc")
        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_special_char(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file(u"trunk/f\x2cle".encode("utf-8"), "data")
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(0))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_signature(self):
        repos_url = self.make_repository('d')
        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file("trunk/bar", "data")
        dc.done()

        self.client_set_revprop(repos_url, 1, "bzr:gpg-signature", "SIGNATURE")
        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(0))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        self.assertEquals("SIGNATURE", newrepos.get_signature_text(oldrepos.generate_revision_id(1, "trunk", oldrepos.get_mapping())))

    def test_fetch_special_char_edit(self):
        repos_url = self.make_repository('d')
        
        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_dir(u'trunk/IöC'.encode("utf-8"))
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_file(u'trunk/IöC/bar'.encode("utf-8"), "more data")
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(0))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_special_char_child(self):
        repos_url = self.make_repository('d')
        
        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_dir(u"trunk/é".encode("utf-8"))
        dc.add_file(u'trunk/é/f\x2cle'.encode("utf-8"), "data")
        dc.done()
        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(0))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_special_char_modify(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file(u"trunk/€\x2c".encode("utf-8"), "data")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_file(u"trunk/€\x2c".encode("utf-8"), "bar")
        revno = dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme(0))
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        self.assertEquals(2, revno)

    def test_fetch_delete(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo/bla': "data"})
        self.client_add("dc/foo")
        self.client_commit("dc", "My Message")
        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        self.client_delete("dc/foo/bla")
        self.client_commit("dc", "Second Message")
        newrepos = Repository.open("f")
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(oldrepos.has_revision(oldrepos.generate_revision_id(2, "", mapping)))

    def test_fetch_delete_recursive(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo/bla': "data"})
        self.client_add("dc/foo")
        self.client_commit("dc", "My Message")
        self.client_delete("dc/foo")
        self.client_commit("dc", "Second Message")
        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        tree = newrepos.revision_tree(oldrepos.generate_revision_id(1, "", mapping))
        self.assertEquals(3, len(tree.inventory))
        tree = newrepos.revision_tree(oldrepos.generate_revision_id(2, "", mapping))
        self.assertEquals(1, len(tree.inventory))

    def test_fetch_local(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/foo/bla': "data"})
        self.client_add("dc/foo")
        self.client_commit("dc", "My Message")
        self.build_tree({'dc/foo/blo': "data2", "dc/bar/foo": "data3", 'dc/foo/bla': "data"})
        self.client_add("dc/foo/blo")
        self.client_add("dc/bar")
        self.client_commit("dc", "Second Message")
        oldrepos = Repository.open(repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(2, "", mapping)))
        newrepos.lock_read()
        try:
            tree = newrepos.revision_tree(
                    oldrepos.generate_revision_id(2, "", mapping))
            self.assertTrue(tree.has_filename("foo/bla"))
            self.assertTrue(tree.has_filename("foo"))
            self.assertEqual("data", tree.get_file_by_path("foo/bla").read())
        finally:
            newrepos.unlock()

    def test_fetch_replace(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/bla': "data"})
        self.client_add("dc/bla")
        self.client_commit("dc", "My Message")
        self.client_delete("dc/bla")
        self.build_tree({'dc/bla': "data2"})
        self.client_add("dc/bla")
        self.client_commit("dc", "Second Message")
        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(2, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(2, "", mapping))
        self.assertNotEqual(inv1.path2id("bla"), inv2.path2id("bla"))

    def test_fetch_copy_subdir(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/trunk/mydir/a': "data"})
        self.client_add("dc/trunk")
        self.client_commit("dc", "My Message")
        self.build_tree({'dc/branches/tmp': None})
        self.client_add("dc/branches")
        self.client_commit("dc", "Second Message")
        self.client_copy("dc/trunk/mydir", "dc/branches/tmp/abranch")
        self.client_commit("dc", "Third Message")
        oldrepos = Repository.open("svn+"+repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_replace_nordic(self):
        filename = os.path.join(self.test_dir, "dumpfile")
        open(filename, 'w').write("""SVN-fs-dump-format-version: 2

UUID: 606c7b1f-987c-4826-b37d-eb556ceb87e1

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2006-12-26T00:04:55.850520Z
PROPS-END

Revision-number: 1
Prop-content-length: 103
Content-length: 103

K 7
svn:log
V 3
add
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:15.504335Z
PROPS-END

Node-path: x\xc3\xa1
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END

Node-path: u\xc3\xa1
Node-path: bla
Node-kind: file
Node-action: add
Prop-content-length: 10
Text-content-length: 5
Text-content-md5: 49803c8f7913948eb3e30bae749ae6bd
Content-length: 15

PROPS-END
bloe


Revision-number: 2
Prop-content-length: 105
Content-length: 105

K 7
svn:log
V 5
readd
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:43.584249Z
PROPS-END

Node-path: x\xc3\xa1
Node-action: delete

""")
        os.mkdir("old")

        load_dumpfile("dumpfile", "old")
        oldrepos = Repository.open("old")
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        self.assertTrue(inv1.has_filename(u"x\xe1"))

    def test_fetch_replace_with_subreplace(self):
        filename = os.path.join(self.test_dir, "dumpfile")
        open(filename, 'w').write("""SVN-fs-dump-format-version: 2

UUID: 606c7b1f-987c-4826-b37d-eb456ceb87e1

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2006-12-26T00:04:55.850520Z
PROPS-END

Revision-number: 1
Prop-content-length: 103
Content-length: 103

K 7
svn:log
V 3
add
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:15.504335Z
PROPS-END

Node-path: x
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END

Node-path: x/t
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END

Node-path: u
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END

Revision-number: 2
Prop-content-length: 105
Content-length: 105

K 7
svn:log
V 5
readd
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:43.584249Z
PROPS-END

Node-path: x
Node-action: delete

Node-path: x
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 3
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Replace

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:30:06.383777Z
PROPS-END

Node-path: x
Node-action: delete

Node-path: y
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: x

Node-path: y/t
Node-action: delete

Node-path: y/t
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: u


""")
        os.mkdir("old")

        load_dumpfile("dumpfile", "old")
        oldrepos = Repository.open("old")
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(3, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(3, "", mapping))

    def test_fetch_replace_self(self):
        filename = os.path.join(self.test_dir, "dumpfile")
        open(filename, 'w').write("""SVN-fs-dump-format-version: 2

UUID: 6dcc86fc-ac21-4df7-a3a3-87616123c853

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2006-12-25T04:27:54.633666Z
PROPS-END

Revision-number: 1
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Add dir

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:28:17.503039Z
PROPS-END

Node-path: bla
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 2
Prop-content-length: 117
Content-length: 117

K 7
svn:log
V 16
Add another dir

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:28:30.160663Z
PROPS-END

Node-path: blie
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 3
Prop-content-length: 105
Content-length: 105

K 7
svn:log
V 5
Copy

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:28:44.996894Z
PROPS-END

Node-path: bloe
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: bla


Revision-number: 4
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Replace

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:30:06.383777Z
PROPS-END

Node-path: bla
Node-action: delete


Node-path: bla
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 2
Node-copyfrom-path: bla


""")
        os.mkdir("old")

        load_dumpfile("dumpfile", "old")
        oldrepos = Repository.open("old")
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(3, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(3, "", mapping))
        self.assertEqual(inv1.path2id("bla"), inv2.path2id("bla"))

    def test_fetch_replace_backup(self):
        filename = os.path.join(self.test_dir, "dumpfile")
        open(filename, 'w').write("""SVN-fs-dump-format-version: 2

UUID: 6dcc86fc-ac21-4df7-a3a3-87616123c853

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2006-12-25T04:27:54.633666Z
PROPS-END

Revision-number: 1
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Add dir

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:28:17.503039Z
PROPS-END

Node-path: bla
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 2
Prop-content-length: 117
Content-length: 117

K 7
svn:log
V 16
Add another dir

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:28:30.160663Z
PROPS-END

Node-path: blie
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 3
Prop-content-length: 105
Content-length: 105

K 7
svn:log
V 5
Copy

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:28:44.996894Z
PROPS-END

Node-path: bloe
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: bla


Revision-number: 4
Prop-content-length: 112
Content-length: 112

K 7
svn:log
V 11
Change bla

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T23:51:09.678679Z
PROPS-END

Node-path: bla
Node-kind: dir
Node-action: change
Prop-content-length: 28
Content-length: 28

K 3
foo
V 5
bloe

PROPS-END


Revision-number: 5
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Replace

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:30:06.383777Z
PROPS-END

Node-path: bla
Node-action: delete


Node-path: bla
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: bla


""")
        os.mkdir("old")

        load_dumpfile("dumpfile", "old")
        oldrepos = Repository.open("old")
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(3, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(3, "", mapping))
        self.assertEqual(inv1.path2id("bla"), inv2.path2id("bla"))

    def test_fetch_replace_unrelated(self):
        filename = os.path.join(self.test_dir, "dumpfile")
        open(filename, 'w').write("""SVN-fs-dump-format-version: 2

UUID: 606c7b1f-987c-4826-b37d-eb456ceb87e1

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2006-12-26T00:04:55.850520Z
PROPS-END

Revision-number: 1
Prop-content-length: 103
Content-length: 103

K 7
svn:log
V 3
add
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:15.504335Z
PROPS-END

Node-path: x
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 2
Prop-content-length: 102
Content-length: 102

K 7
svn:log
V 2
rm
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:30.775369Z
PROPS-END

Node-path: x
Node-action: delete


Revision-number: 3
Prop-content-length: 105
Content-length: 105

K 7
svn:log
V 5
readd
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:43.584249Z
PROPS-END

Node-path: x
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 4
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Replace

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:30:06.383777Z
PROPS-END

Node-path: x
Node-action: delete


Node-path: x
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: x

                
""")
        os.mkdir("old")

        load_dumpfile("dumpfile", "old")
        oldrepos = Repository.open("old")
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(4, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(4, "", mapping))
        self.assertNotEqual(inv1.path2id("x"), inv2.path2id("x"))

    def test_fetch_replace_related(self):
        filename = os.path.join(self.test_dir, "dumpfile")
        open(filename, 'w').write("""SVN-fs-dump-format-version: 2

UUID: 606c7b1f-987c-4826-b37d-eb456ceb87e1

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2006-12-26T00:04:55.850520Z
PROPS-END

Revision-number: 1
Prop-content-length: 103
Content-length: 103

K 7
svn:log
V 3
add
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:15.504335Z
PROPS-END

Node-path: x
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 2
Prop-content-length: 102
Content-length: 102

K 7
svn:log
V 2
rm
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:30.775369Z
PROPS-END

Node-path: x
Node-action: delete


Revision-number: 3
Prop-content-length: 105
Content-length: 105

K 7
svn:log
V 5
readd
K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-26T00:05:43.584249Z
PROPS-END

Node-path: y
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: x
Prop-content-length: 10
Content-length: 10

PROPS-END


Revision-number: 4
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Replace

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:30:06.383777Z
PROPS-END

Node-path: y
Node-action: delete


Revision-number: 5
Prop-content-length: 108
Content-length: 108

K 7
svn:log
V 8
Replace

K 10
svn:author
V 6
jelmer
K 8
svn:date
V 27
2006-12-25T04:30:06.383777Z
PROPS-END


Node-path: y
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: x


""")
        os.mkdir("old")

        load_dumpfile("dumpfile", "old")
        oldrepos = Repository.open("old")
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(5, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(5, "", mapping))
        self.assertNotEqual(inv1.path2id("y"), inv2.path2id("y"))

    def test_fetch_dir_upgrade(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_dir("trunk/lib")
        dc.add_file("trunk/lib/file", 'data')
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_dir("branches")
        dc.add_dir("branches/mybranch", "trunk/lib")
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

        branch = Branch.open("%s/branches/mybranch" % repos_url)
        mapping = oldrepos.get_mapping()
        self.assertEqual([oldrepos.generate_revision_id(2, "branches/mybranch", mapping)], 
                         branch.revision_history())

    def test_fetch_file_from_non_branch(self):
        repos_url = self.make_client('d', 'dc')

        self.build_tree({'dc/old-trunk/lib/file': 'data'})
        self.client_add("dc/old-trunk")
        self.client_commit("dc", "trunk data")

        self.build_tree({'dc/trunk/lib': None})
        self.client_add("dc/trunk")
        self.client_copy("dc/old-trunk/lib/file", "dc/trunk/lib/file")
        self.client_commit("dc", "revive old trunk")

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

        branch = Branch.open("%s/trunk" % repos_url)
        self.assertEqual([oldrepos.generate_revision_id(2, "trunk", oldrepos.get_mapping())], 
                         branch.revision_history())

    def test_fetch_dir_from_non_branch(self):
        repos_url = self.make_client('d', 'dc')

        self.build_tree({'dc/old-trunk/lib/file': 'data'})
        self.client_add("dc/old-trunk")
        self.client_commit("dc", "trunk data")

        self.build_tree({'dc/trunk': None})
        self.client_add("dc/trunk")
        self.client_copy("dc/old-trunk/lib", "dc/trunk")
        self.client_commit("dc", "revive old trunk")

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

        branch = Branch.open("%s/trunk" % repos_url)
        self.assertEqual([oldrepos.generate_revision_id(2, "trunk", oldrepos.get_mapping())],
                         branch.revision_history())

    def test_fetch_from_non_branch(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("old-trunk")
        dc.add_dir("old-trunk/lib")
        dc.add_file("old-trunk/lib/file", "data")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk", "old-trunk")
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

        branch = Branch.open("%s/trunk" % repos_url)
        self.assertEqual([oldrepos.generate_revision_id(2, "trunk", oldrepos.get_mapping())],
                         branch.revision_history())



    def test_fetch_branch_downgrade(self):
        repos_url = self.make_client('d', 'dc')

        self.build_tree({'dc/trunk/file': 'data'})
        self.client_add("dc/trunk")
        self.client_commit("dc", "trunk data")

        self.build_tree({'dc/branches/mybranch': None})
        self.client_add("dc/branches")
        self.client_copy("dc/trunk", "dc/branches/mybranch/lib")
        self.client_commit("dc", "split out lib")

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

    def test_fetch_all(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file("trunk/hosts", 'hej1')
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_file('trunk/hosts', 'hej2')
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_file('trunk/hosts', 'hej3')
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.add_dir("branches")
        dc.add_dir("branches/foobranch")
        dc.add_file("branches/foobranch/file", 'foohosts')
        dc.done()

        oldrepos = Repository.open(repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

        mapping = oldrepos.get_mapping()

        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "trunk", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(2, "trunk", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(3, "trunk", mapping)))
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(4, "branches/foobranch", mapping)))
        self.assertFalse(newrepos.has_revision(
            oldrepos.generate_revision_id(4, "trunk", mapping)))
        self.assertFalse(newrepos.has_revision(
            oldrepos.generate_revision_id(2, "", mapping)))

    def test_fetch_copy_root_id_kept(self):
        repos_url = self.make_client('d', 'dc')

        self.build_tree({'dc/trunk': None, 
                         'dc/trunk/hosts': 'hej1'})
        self.client_add("dc/trunk")
        self.client_commit("dc", "created trunk and added hosts") #1

        self.build_tree({'dc/branches': None})
        self.client_add("dc/branches")
        self.client_commit("dc", "added branches") #2

        self.client_copy("dc/trunk", "dc/branches/foobranch")
        self.client_commit("dc", "added branch foobranch") #3

        repos = remote.SvnRemoteAccess(SvnRaTransport("svn+"+repos_url), format.SvnRemoteFormat()).find_repository()
        set_branching_scheme(repos, TrunkBranchingScheme())

        mapping = repos.get_mapping()

        tree = repos.revision_tree(
             repos.generate_revision_id(3, "branches/foobranch", mapping))

        self.assertEqual(mapping.generate_file_id(repos.uuid, 1, "trunk", u""), tree.inventory.root.file_id)

    def test_fetch_odd(self):
        repos_url = self.make_client('d', 'dc')

        self.build_tree({'dc/trunk': None, 
                         'dc/trunk/hosts': 'hej1'})
        self.client_add("dc/trunk")
        self.client_commit("dc", "created trunk and added hosts") #1
        self.client_update("dc")

        self.build_tree({'dc/trunk/hosts': 'hej2'})
        self.client_commit("dc", "rev 2") #2
        self.client_update("dc")

        self.build_tree({'dc/trunk/hosts': 'hej3'})
        self.client_commit("dc", "rev 3") #3
        self.client_update("dc")

        self.build_tree({'dc/branches': None})
        self.client_add("dc/branches")
        self.client_commit("dc", "added branches") #4
        self.client_update("dc")

        self.client_copy("dc/trunk", "dc/branches/foobranch")
        self.client_commit("dc", "added branch foobranch") #5
        self.client_update("dc")

        self.build_tree({'dc/branches/foobranch/hosts': 'foohosts'})
        self.client_commit("dc", "foohosts") #6

        repos = remote.SvnRemoteAccess(SvnRaTransport("svn+"+repos_url), format.SvnRemoteFormat()).find_repository()
        set_branching_scheme(repos, TrunkBranchingScheme())

        mapping = repos.get_mapping()

        tree = repos.revision_tree(
             repos.generate_revision_id(6, "branches/foobranch", mapping))

    def test_fetch_consistent(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_file("bla", "data")
        dc.change_file_prop("bla", "svn:executable", "*")
        dc.done()

        oldrepos = Repository.open("svn+"+repos_url)
        dir1 = BzrDir.create("f", format.get_rich_root_format())
        dir2 = BzrDir.create("g", format.get_rich_root_format())
        newrepos1 = dir1.create_repository()
        newrepos2 = dir2.create_repository()
        oldrepos.copy_content_into(newrepos1)
        oldrepos.copy_content_into(newrepos2)
        mapping = oldrepos.get_mapping()
        inv1 = newrepos1.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos2.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        self.assertEqual(inv1, inv2)

    def test_fetch_executable(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/bla': "data", 'dc/blie': "data2"})
        self.client_add("dc/bla")
        self.client_add("dc/blie")
        self.client_set_prop("dc/bla", "svn:executable", "*")
        self.client_set_prop("dc/blie", "svn:executable", "")
        self.client_commit("dc", "My Message")
        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        self.assertTrue(inv1[inv1.path2id("bla")].executable)
        self.assertTrue(inv1[inv1.path2id("blie")].executable)

    def test_fetch_symlink(self):
        if not has_symlinks():
            return
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/bla': "data"})
        os.symlink('bla', 'dc/mylink')
        self.client_add("dc/bla")
        self.client_add("dc/mylink")
        self.client_commit("dc", "My Message")
        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        self.assertEqual('symlink', inv1[inv1.path2id("mylink")].kind)
        self.assertEqual('bla', inv1[inv1.path2id("mylink")].symlink_target)

    def test_fetch_symlink_kind_change(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/bla': "data", "dc/mylink": "link bla"})
        self.client_add("dc/bla")
        self.client_add("dc/mylink")
        self.client_commit("dc", "My Message")
        ra = SvnRaTransport(repos_url)
        def done(info, pool):
            pass
        editor = ra.get_commit_editor({"svn:log": "msg"}, done, None, False)
        root_baton = editor.open_root(1)
        baton = root_baton.open_file("mylink", 1)
        baton.change_prop("svn:special", "*")
        baton.close()
        root_baton.close()
        editor.close()
        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(2, "", mapping))
        self.assertEqual('file', inv1[inv1.path2id("mylink")].kind)
        self.assertEqual('symlink', inv2[inv2.path2id("mylink")].kind)
        self.assertEqual('bla', inv2[inv2.path2id("mylink")].symlink_target)

    def test_fetch_executable_separate(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/bla': "data"})
        self.client_add("dc/bla")
        self.client_commit("dc", "My Message")
        self.client_set_prop("dc/bla", "svn:executable", "*")
        self.client_commit("dc", "Make executable")
        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertTrue(newrepos.has_revision(
            oldrepos.generate_revision_id(1, "", mapping)))
        inv1 = newrepos.get_inventory(
                oldrepos.generate_revision_id(1, "", mapping))
        self.assertFalse(inv1[inv1.path2id("bla")].executable)
        inv2 = newrepos.get_inventory(
                oldrepos.generate_revision_id(2, "", mapping))
        self.assertTrue(inv2[inv2.path2id("bla")].executable)
        self.assertEqual(oldrepos.generate_revision_id(2, "", mapping), 
                         inv2[inv2.path2id("bla")].revision)

    def test_fetch_ghosts(self):
        repos_url = self.make_repository('d')

        dc = self.commit_editor(repos_url)
        dc.add_file("bla", "data")
        dc.change_dir_prop("", "bzr:ancestry:v3-none", "aghost\n")
        dc.done()

        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()

        rev = newrepos.get_revision(oldrepos.generate_revision_id(1, "", mapping))
        self.assertTrue("aghost" in rev.parent_ids)

    def test_fetch_svk_merge(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/trunk/bla': "data", "dc/branches": None})
        self.client_add("dc/trunk")
        self.client_commit("dc", "My Message")

        self.client_add("dc/branches")
        self.client_copy("dc/trunk", "dc/branches/foo")
        self.build_tree({'dc/branches/foo/bla': "more data"})
        self.client_commit("dc", "Branch")

        oldrepos = Repository.open("svn+"+repos_url)
        self.client_set_prop("dc/trunk", "svk:merge", 
                             "%s:/branches/foo:2\n" % oldrepos.uuid)
        self.client_commit("dc", "Merge")

        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)

        mapping = oldrepos.get_mapping()

        rev = newrepos.get_revision(oldrepos.generate_revision_id(3, "trunk", mapping))
        mutter('parent ids: %r' % rev.parent_ids)
        self.assertTrue(oldrepos.generate_revision_id(2, "branches/foo", mapping) in rev.parent_ids)

    def test_fetch_invalid_ghosts(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/bla': "data"})
        self.client_add("dc/bla")
        self.client_set_prop("dc", "bzr:ancestry:v3-none", "a ghost\n")
        self.client_commit("dc", "My Message")
        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        
        mapping = oldrepos.get_mapping()

        rev = newrepos.get_revision(oldrepos.generate_revision_id(1, "", mapping))
        self.assertEqual([oldrepos.generate_revision_id(0, "", mapping)], rev.parent_ids)

    def test_fetch_property_change_only(self):
        repos_url = self.make_repository('d')
        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file("trunk/bla", "data")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_dir_prop("", "some:property", "some data\n")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_dir_prop("", "some2:property", "some data\n")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_dir_prop("", "some:property", "some data4\n")
        dc.done()

        oldrepos = Repository.open("svn+"+repos_url)
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertEquals([
            oldrepos.generate_revision_id(0, "", mapping),
            oldrepos.generate_revision_id(1, "", mapping),
            oldrepos.generate_revision_id(2, "", mapping),
            oldrepos.generate_revision_id(3, "", mapping),
            oldrepos.generate_revision_id(4, "", mapping),
            ], newrepos.all_revision_ids())

    def test_fetch_property_change_only_trunk(self):
        repos_url = self.make_repository('d')
        dc = self.commit_editor(repos_url)
        dc.add_dir("trunk")
        dc.add_file("trunk/bla", "data")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_dir_prop("trunk", "some:property", "some data\n")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_dir_prop("trunk", "some2:property", "some data\n")
        dc.done()

        dc = self.commit_editor(repos_url)
        dc.change_dir_prop("trunk", "some:property", "some data3\n")
        dc.done()

        oldrepos = Repository.open("svn+"+repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        oldrepos.copy_content_into(newrepos)
        mapping = oldrepos.get_mapping()
        self.assertEquals([
            oldrepos.generate_revision_id(1, "trunk", mapping),
            oldrepos.generate_revision_id(2, "trunk", mapping),
            oldrepos.generate_revision_id(3, "trunk", mapping),
            oldrepos.generate_revision_id(4, "trunk", mapping),
            ], newrepos.all_revision_ids())

    def test_fetch_crosscopy(self):
        repos_url = self.make_client('d', 'dc')
        self.build_tree({'dc/trunk/adir/afile': "data", 
                         'dc/trunk/adir/stationary': None,
                         'dc/branches/abranch': None})
        self.client_add("dc/trunk")
        self.client_add("dc/branches")
        self.client_commit("dc", "Initial commit")

        # copyrev
        self.client_copy("dc/trunk/adir", "dc/branches/abranch/bdir")
        self.client_commit("dc", "Cross copy commit")

        # prevrev
        self.build_tree({"dc/branches/abranch/bdir/afile": "otherdata"})
        self.client_commit("dc", "Change data")

        # lastrev
        self.build_tree({"dc/branches/abranch/bdir/bfile": "camel",
                      "dc/branches/abranch/bdir/stationary/traveller": "data"})
        self.client_add("dc/branches/abranch/bdir/bfile")
        self.client_add("dc/branches/abranch/bdir/stationary/traveller")
        self.client_commit("dc", "Change dir")

        oldrepos = Repository.open("svn+"+repos_url)
        set_branching_scheme(oldrepos, TrunkBranchingScheme())
        dir = BzrDir.create("f", format.get_rich_root_format())
        newrepos = dir.create_repository()
        mapping = oldrepos.get_mapping()
        copyrev = oldrepos.generate_revision_id(2, "branches/abranch", mapping)
        prevrev = oldrepos.generate_revision_id(3, "branches/abranch", mapping)
        lastrev = oldrepos.generate_revision_id(4, "branches/abranch", mapping)
        oldrepos.copy_content_into(newrepos, lastrev)

        inventory = newrepos.get_inventory(lastrev)
        self.assertEqual(prevrev, 
                         inventory[inventory.path2id("bdir/afile")].revision)

        inventory = newrepos.get_inventory(prevrev)
        self.assertEqual(copyrev, 
                         inventory[inventory.path2id("bdir/stationary")].revision)


