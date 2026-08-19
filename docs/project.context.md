# ctxpack Context Pack

Generated from: `/workspace`
Files included: 42
⚠️ **WARNING**: Total repository tokens exceeded the budget. Some files are truncated or omitted.

---

## .ctxignore
Size: 216 bytes | Est. tokens: 54

```text
# ctxpack ignore patterns (gitignore-style)
.git/
.svn/
.hg/
__pycache__/
*.pyc
*.pyo
node_modules/
venv/
.venv/
dist/
build/
*.log
*.lock
package-lock.json
.DS_Store
Thumbs.db
ctxpack.context.json
ctxpack.context.md
```

## .git/COMMIT_EDITMSG
Size: 648 bytes | Est. tokens: 162

```text
feat: upgrade to v0.2.0 with include/exclude patterns, custom output paths, and budget warnings

- Add --include/--exclude flags for fine-grained file selection
- Add --output-dir and --base-name for flexible output locations
- Add is_incomplete flag and warning in outputs when budget exceeded
- Add human-readable summary printed to stdout after pack
- Expand ctxpack.json config with include, exclude, output_dir, base_name
- Refactor should_ignore() to matches_pattern() + should_process()
- Add GitHub Actions CI workflow for multi-version Python testing
- Add pyproject.toml for PyPI readiness (v0.2.0)
- Update tests to match new v0.2.0 API

```

## .git/FETCH_HEAD
Size: 103 bytes | Est. tokens: 25

```text
9050c6d6b82f98da7dba855b11b498f6a3ef06f9		branch 'main' of https://github.com/billybox1926-jpg/ctxpack

```

## .git/HEAD
Size: 63 bytes | Est. tokens: 15

```text
ref: refs/heads/qwen-code-9e9a5a4b-551a-4e28-a096-b2cab196ebe1

```

## .git/config
Size: 92 bytes | Est. tokens: 23

```text
[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true

```

## .git/description
Size: 73 bytes | Est. tokens: 18

```text
Unnamed repository; edit this file 'description' to name the repository.

```

## .git/hooks/applypatch-msg.sample
Size: 478 bytes | Est. tokens: 119

```text
#!/bin/sh
#
# An example hook script to check the commit log message taken by
# applypatch from an e-mail message.
#
# The hook should exit with non-zero status after issuing an
# appropriate message if it wants to stop the commit.  The hook is
# allowed to edit the commit message file.
#
# To enable this hook, rename this file to "applypatch-msg".

. git-sh-setup
commitmsg="$(git rev-parse --git-path hooks/commit-msg)"
test -x "$commitmsg" && exec "$commitmsg" ${1+"$@"}
:

```

## .git/hooks/commit-msg.sample
Size: 896 bytes | Est. tokens: 224

```text
#!/bin/sh
#
# An example hook script to check the commit log message.
# Called by "git commit" with one argument, the name of the file
# that has the commit message.  The hook should exit with non-zero
# status after issuing an appropriate message if it wants to stop the
# commit.  The hook is allowed to edit the commit message file.
#
# To enable this hook, rename this file to "commit-msg".

# Uncomment the below to add a Signed-off-by line to the message.
# Doing this in a hook is a bad idea in general, but the prepare-commit-msg
# hook is more suited to it.
#
# SOB=$(git var GIT_AUTHOR_IDENT | sed -n 's/^\(.*>\).*$/Signed-off-by: \1/p')
# grep -qs "^$SOB" "$1" || echo "$SOB" >> "$1"

# This example catches duplicate Signed-off-by lines.

test "" = "$(grep '^Signed-off-by: ' "$1" |
	 sort | uniq -c | sed -e '/^[ 	]*1[ 	]/d')" || {
	echo >&2 Duplicate Signed-off-by lines.
	exit 1
}

```

## .git/hooks/fsmonitor-watchman.sample
Size: 4726 bytes | Est. tokens: 1181

```text
#!/usr/bin/perl

use strict;
use warnings;
use IPC::Open2;

# An example hook script to integrate Watchman
# (https://facebook.github.io/watchman/) with git to speed up detecting
# new and modified files.
#
# The hook is passed a version (currently 2) and last update token
# formatted as a string and outputs to stdout a new update token and
# all files that have been modified since the update token. Paths must
# be relative to the root of the working tree and separated by a single NUL.
#
# To enable this hook, rename this file to "query-watchman" and set
# 'git config core.fsmonitor .git/hooks/query-watchman'
#
my ($version, $last_update_token) = @ARGV;

# Uncomment for debugging
# print STDERR "$0 $version $last_update_token\n";

# Check the hook interface version
if ($version ne 2) {
	die "Unsupported query-fsmonitor hook version '$version'.\n" .
	    "Falling back to scanning...\n";
}

my $git_work_tree = get_working_dir();

my $retry = 1;

my $json_pkg;
eval {
	require JSON::XS;
	$json_pkg = "JSON::XS";
	1;
} or do {
	require JSON::PP;
	$json_pkg = "JSON::PP";
};

launch_watchman();

sub launch_watchman {
	my $o = watchman_query();
	if (is_work_tree_watched($o)) {
		output_result($o->{clock}, @{$o->{files}});
	}
}

sub output_result {
	my ($clockid, @files) = @_;

	# Uncomment for debugging watchman output
	# open (my $fh, ">", ".git/watchman-output.out");
	# binmode $fh, ":utf8";
	# print $fh "$clockid\n@files\n";
	# close $fh;

	binmode STDOUT, ":utf8";
	print $clockid;
	print "\0";
	local $, = "\0";
	print @files;
}

sub watchman_clock {
	my $response = qx/watchman clock "$git_work_tree"/;
	die "Failed to get clock id on '$git_work_tree'.\n" .
		"Falling back to scanning...\n" if $? != 0;

	return $json_pkg->new->utf8->decode($response);
}

sub watchman_query {
	my $pid = open2(\*CHLD_OUT, \*CHLD_IN, 'watchman -j --no-pretty')
	or die "open2() failed: $!\n" .
	"Falling back to scanning...\n";

	# In the query expression below we're asking for names of files that
	# changed since $last_update_token but not from the .git folder.
	#
	# To accomplish this, we're using the "since" generator to use the
	# recency index to select candidate nodes and "fields" to limit the
	# output to file names only. Then we're using the "expression" term to
	# further constrain the results.
	my $last_update_line = "";
	if (substr($last_update_token, 0, 1) eq "c") {
		$last_update_token = "\"$last_update_token\"";
		$last_update_line = qq[\n"since": $last_update_token,];
	}
	my $query = <<"	END";
		["query", "$git_work_tree", {$last_update_line
			"fields": ["name"],
			"expression": ["not", ["dirname", ".git"]]
		}]
	END

	# Uncomment for debugging the watchman query
	# open (my $fh, ">", ".git/watchman-query.json");
	# print $fh $query;
	# close $fh;

	print CHLD_IN $query;
	close CHLD_IN;
	my $response = do {local $/; <CHLD_OUT>};

	# Uncomment for debugging the watch response
	# open ($fh, ">", ".git/watchman-response.json");
	# print $fh $response;
	# close $fh;

	die "Watchman: command returned no output.\n" .
	"Falling back to scanning...\n" if $response eq "";
	die "Watchman: command returned invalid output: $response\n" .
	"Falling back to scanning...\n" unless $response =~ /^\{/;

	return $json_pkg->new->utf8->decode($response);
}

sub is_work_tree_watched {
	my ($output) = @_;
	my $error = $output->{error};
	if ($retry > 0 and $error and $error =~ m/unable to resolve root .* directory (.*) is not watched/) {
		$retry--;
		my $response = qx/watchman watch "$git_work_tree"/;
		die "Failed to make watchman watch '$git_work_tree'.\n" .
		    "Falling back to scanning...\n" if $? != 0;
		$output = $json_pkg->new->utf8->decode($response);
		$error = $output->{error};
		die "Watchman: $error.\n" .
		"Falling back to scanning...\n" if $error;

		# Uncomment for debugging watchman output
		# open (my $fh, ">", ".git/watchman-output.out");
		# close $fh;

		# Watchman will always return all files on the first query so
		# return the fast "everything is dirty" flag to git and do the
		# Watchman query just to get it over with now so we won't pay
		# the cost in git to look up each individual file.
		my $o = watchman_clock();
		$error = $output->{error};

		die "Watchman: $error.\n" .
		"Falling back to scanning...\n" if $error;

		output_result($o->{clock}, ("/"));
		$last_update_token = $o->{clock};

		eval { launch_watchman() };
		return 0;
	}

	die "Watchman: $error.\n" .
	"Falling back to scanning...\n" if $error;

	return 1;
}

sub get_working_dir {
	my $working_dir;
	if ($^O =~ 'msys' || $^O =~ 'cygwin') {
		$working_dir = Win32::GetCwd();
		$working_dir =~ tr/\\/\//;
	} else {
		require Cwd;
		$working_dir = Cwd::cwd();
	}

	return $working_dir;
}

```

## .git/hooks/post-update.sample
Size: 189 bytes | Est. tokens: 47

```text
#!/bin/sh
#
# An example hook script to prepare a packed repository for use over
# dumb transports.
#
# To enable this hook, rename this file to "post-update".

exec git update-server-info

```

## .git/hooks/pre-applypatch.sample
Size: 424 bytes | Est. tokens: 106

```text
#!/bin/sh
#
# An example hook script to verify what is about to be committed
# by applypatch from an e-mail message.
#
# The hook should exit with non-zero status after issuing an
# appropriate message if it wants to stop the commit.
#
# To enable this hook, rename this file to "pre-applypatch".

. git-sh-setup
precommit="$(git rev-parse --git-path hooks/pre-commit)"
test -x "$precommit" && exec "$precommit" ${1+"$@"}
:

```

## .git/hooks/pre-commit.sample
Size: 1643 bytes | Est. tokens: 410

```text
#!/bin/sh
#
# An example hook script to verify what is about to be committed.
# Called by "git commit" with no arguments.  The hook should
# exit with non-zero status after issuing an appropriate message if
# it wants to stop the commit.
#
# To enable this hook, rename this file to "pre-commit".

if git rev-parse --verify HEAD >/dev/null 2>&1
then
	against=HEAD
else
	# Initial commit: diff against an empty tree object
	against=$(git hash-object -t tree /dev/null)
fi

# If you want to allow non-ASCII filenames set this variable to true.
allownonascii=$(git config --type=bool hooks.allownonascii)

# Redirect output to stderr.
exec 1>&2

# Cross platform projects tend to avoid non-ASCII filenames; prevent
# them from being added to the repository. We exploit the fact that the
# printable range starts at the space character and ends with tilde.
if [ "$allownonascii" != "true" ] &&
	# Note that the use of brackets around a tr range is ok here, (it's
	# even required, for portability to Solaris 10's /usr/bin/tr), since
	# the square bracket bytes happen to fall in the designated range.
	test $(git diff --cached --name-only --diff-filter=A -z $against |
	  LC_ALL=C tr -d '[ -~]\0' | wc -c) != 0
then
	cat <<\EOF
Error: Attempt to add a non-ASCII file name.

This can cause problems if you want to work with people on other platforms.

To be portable it is advisable to rename the file.

If you know what you are doing you can disable this check using:

  git config hooks.allownonascii true
EOF
	exit 1
fi

# If there are whitespace errors, print the offending file names and fail.
exec git diff-index --check --cached $against --

```

## .git/hooks/pre-merge-commit.sample
Size: 416 bytes | Est. tokens: 104

```text
#!/bin/sh
#
# An example hook script to verify what is about to be committed.
# Called by "git merge" with no arguments.  The hook should
# exit with non-zero status after issuing an appropriate message to
# stderr if it wants to stop the merge commit.
#
# To enable this hook, rename this file to "pre-merge-commit".

. git-sh-setup
test -x "$GIT_DIR/hooks/pre-commit" &&
        exec "$GIT_DIR/hooks/pre-commit"
:

```

## .git/hooks/pre-push.sample
Size: 1374 bytes | Est. tokens: 343

```text
#!/bin/sh

# An example hook script to verify what is about to be pushed.  Called by "git
# push" after it has checked the remote status, but before anything has been
# pushed.  If this script exits with a non-zero status nothing will be pushed.
#
# This hook is called with the following parameters:
#
# $1 -- Name of the remote to which the push is being done
# $2 -- URL to which the push is being done
#
# If pushing without using a named remote those arguments will be equal.
#
# Information about the commits which are being pushed is supplied as lines to
# the standard input in the form:
#
#   <local ref> <local oid> <remote ref> <remote oid>
#
# This sample shows how to prevent push of commits where the log message starts
# with "WIP" (work in progress).

remote="$1"
url="$2"

zero=$(git hash-object --stdin </dev/null | tr '[0-9a-f]' '0')

while read local_ref local_oid remote_ref remote_oid
do
	if test "$local_oid" = "$zero"
	then
		# Handle delete
		:
	else
		if test "$remote_oid" = "$zero"
		then
			# New branch, examine all commits
			range="$local_oid"
		else
			# Update to existing branch, examine new commits
			range="$remote_oid..$local_oid"
		fi

		# Check for WIP commit
		commit=$(git rev-list -n 1 --grep '^WIP' "$range")
		if test -n "$commit"
		then
			echo >&2 "Found WIP commit in $local_ref, not pushing"
			exit 1
		fi
	fi
done

exit 0

```

## .git/hooks/pre-rebase.sample
Size: 4898 bytes | Est. tokens: 1224

```text
#!/bin/sh
#
# Copyright (c) 2006, 2008 Junio C Hamano
#
# The "pre-rebase" hook is run just before "git rebase" starts doing
# its job, and can prevent the command from running by exiting with
# non-zero status.
#
# The hook is called with the following parameters:
#
# $1 -- the upstream the series was forked from.
# $2 -- the branch being rebased (or empty when rebasing the current branch).
#
# This sample shows how to prevent topic branches that are already
# merged to 'next' branch from getting rebased, because allowing it
# would result in rebasing already published history.

publish=next
basebranch="$1"
if test "$#" = 2
then
	topic="refs/heads/$2"
else
	topic=`git symbolic-ref HEAD` ||
	exit 0 ;# we do not interrupt rebasing detached HEAD
fi

case "$topic" in
refs/heads/??/*)
	;;
*)
	exit 0 ;# we do not interrupt others.
	;;
esac

# Now we are dealing with a topic branch being rebased
# on top of master.  Is it OK to rebase it?

# Does the topic really exist?
git show-ref -q "$topic" || {
	echo >&2 "No such branch $topic"
	exit 1
}

# Is topic fully merged to master?
not_in_master=`git rev-list --pretty=oneline ^master "$topic"`
if test -z "$not_in_master"
then
	echo >&2 "$topic is fully merged to master; better remove it."
	exit 1 ;# we could allow it, but there is no point.
fi

# Is topic ever merged to next?  If so you should not be rebasing it.
only_next_1=`git rev-list ^master "^$topic" ${publish} | sort`
only_next_2=`git rev-list ^master           ${publish} | sort`
if test "$only_next_1" = "$only_next_2"
then
	not_in_topic=`git rev-list "^$topic" master`
	if test -z "$not_in_topic"
	then
		echo >&2 "$topic is already up to date with master"
		exit 1 ;# we could allow it, but there is no point.
	else
		exit 0
	fi
else
	not_in_next=`git rev-list --pretty=oneline ^${publish} "$topic"`
	/usr/bin/perl -e '
		my $topic = $ARGV[0];
		my $msg = "* $topic has commits already merged to public branch:\n";
		my (%not_in_next) = map {
			/^([0-9a-f]+) /;
			($1 => 1);
		} split(/\n/, $ARGV[1]);
		for my $elem (map {
				/^([0-9a-f]+) (.*)$/;
				[$1 => $2];
			} split(/\n/, $ARGV[2])) {
			if (!exists $not_in_next{$elem->[0]}) {
				if ($msg) {
					print STDERR $msg;
					undef $msg;
				}
				print STDERR " $elem->[1]\n";
			}
		}
	' "$topic" "$not_in_next" "$not_in_master"
	exit 1
fi

<<\DOC_END

This sample hook safeguards topic branches that have been
published from being rewound.

The workflow assumed here is:

 * Once a topic branch forks from "master", "master" is never
   merged into it again (either directly or indirectly).

 * Once a topic branch is fully cooked and merged into "master",
   it is deleted.  If you need to build on top of it to correct
   earlier mistakes, a new topic branch is created by forking at
   the tip of the "master".  This is not strictly necessary, but
   it makes it easier to keep your history simple.

 * Whenever you need to test or publish your changes to topic
   branches, merge them into "next" branch.

The script, being an example, hardcodes the publish branch name
to be "next", but it is trivial to make it configurable via
$GIT_DIR/config mechanism.

With this workflow, you would want to know:

(1) ... if a topic branch has ever been merged to "next".  Young
    topic branches can have stupid mistakes you would rather
    clean up before publishing, and things that have not been
    merged into other branches can be easily rebased without
    affecting other people.  But once it is published, you would
    not want to rewind it.

(2) ... if a topic branch has been fully merged to "master".
    Then you can delete it.  More importantly, you should not
    build on top of it -- other people may already want to
    change things related to the topic as patches against your
    "master", so if you need further changes, it is better to
    fork the topic (perhaps with the same name) afresh from the
    tip of "master".

Let's look at this example:

		   o---o---o---o---o---o---o---o---o---o "next"
		  /       /           /           /
		 /   a---a---b A     /           /
		/   /               /           /
	       /   /   c---c---c---c B         /
	      /   /   /             \         /
	     /   /   /   b---b C     \       /
	    /   /   /   /             \     /
    ---o---o---o---o---o---o---o---o---o---o---o "master"


A, B and C are topic branches.

 * A has one fix since it was merged up to "next".

 * B has finished.  It has been fully merged up to "master" and "next",
   and is ready to be deleted.

 * C has not merged to "next" at all.

We would want to allow C to be rebased, refuse A, and encourage
B to be deleted.

To compute (1):

	git rev-list ^master ^topic next
	git rev-list ^master        next

	if these match, topic has not merged in next at all.

To compute (2):

	git rev-list master..topic

	if this is empty, it is fully merged to "master".

DOC_END

```

## .git/hooks/pre-receive.sample
Size: 544 bytes | Est. tokens: 136

```text
#!/bin/sh
#
# An example hook script to make use of push options.
# The example simply echoes all push options that start with 'echoback='
# and rejects all pushes when the "reject" push option is used.
#
# To enable this hook, rename this file to "pre-receive".

if test -n "$GIT_PUSH_OPTION_COUNT"
then
	i=0
	while test "$i" -lt "$GIT_PUSH_OPTION_COUNT"
	do
		eval "value=\$GIT_PUSH_OPTION_$i"
		case "$value" in
		echoback=*)
			echo "echo from the pre-receive-hook: ${value#*=}" >&2
			;;
		reject)
			exit 1
		esac
		i=$((i + 1))
	done
fi

```

## .git/hooks/prepare-commit-msg.sample
Size: 1492 bytes | Est. tokens: 373

```text
#!/bin/sh
#
# An example hook script to prepare the commit log message.
# Called by "git commit" with the name of the file that has the
# commit message, followed by the description of the commit
# message's source.  The hook's purpose is to edit the commit
# message file.  If the hook fails with a non-zero status,
# the commit is aborted.
#
# To enable this hook, rename this file to "prepare-commit-msg".

# This hook includes three examples. The first one removes the
# "# Please enter the commit message..." help message.
#
# The second includes the output of "git diff --name-status -r"
# into the message, just before the "git status" output.  It is
# commented because it doesn't cope with --amend or with squashed
# commits.
#
# The third example adds a Signed-off-by line to the message, that can
# still be edited.  This is rarely a good idea.

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2
SHA1=$3

/usr/bin/perl -i.bak -ne 'print unless(m/^. Please enter the commit message/..m/^#$/)' "$COMMIT_MSG_FILE"

# case "$COMMIT_SOURCE,$SHA1" in
#  ,|template,)
#    /usr/bin/perl -i.bak -pe '
#       print "\n" . `git diff --cached --name-status -r`
# 	 if /^#/ && $first++ == 0' "$COMMIT_MSG_FILE" ;;
#  *) ;;
# esac

# SOB=$(git var GIT_COMMITTER_IDENT | sed -n 's/^\(.*>\).*$/Signed-off-by: \1/p')
# git interpret-trailers --in-place --trailer "$SOB" "$COMMIT_MSG_FILE"
# if test -z "$COMMIT_SOURCE"
# then
#   /usr/bin/perl -i.bak -pe 'print "\n" if !$first_line++' "$COMMIT_MSG_FILE"
# fi

```

## .git/hooks/push-to-checkout.sample
Size: 2783 bytes | Est. tokens: 695

```text
#!/bin/sh

# An example hook script to update a checked-out tree on a git push.
#
# This hook is invoked by git-receive-pack(1) when it reacts to git
# push and updates reference(s) in its repository, and when the push
# tries to update the branch that is currently checked out and the
# receive.denyCurrentBranch configuration variable is set to
# updateInstead.
#
# By default, such a push is refused if the working tree and the index
# of the remote repository has any difference from the currently
# checked out commit; when both the working tree and the index match
# the current commit, they are updated to match the newly pushed tip
# of the branch. This hook is to be used to override the default
# behaviour; however the code below reimplements the default behaviour
# as a starting point for convenient modification.
#
# The hook receives the commit with which the tip of the current
# branch is going to be updated:
commit=$1

# It can exit with a non-zero status to refuse the push (when it does
# so, it must not modify the index or the working tree).
die () {
	echo >&2 "$*"
	exit 1
}

# Or it can make any necessary changes to the working tree and to the
# index to bring them to the desired state when the tip of the current
# branch is updated to the new commit, and exit with a zero status.
#
# For example, the hook can simply run git read-tree -u -m HEAD "$1"
# in order to emulate git fetch that is run in the reverse direction
# with git push, as the two-tree form of git read-tree -u -m is
# essentially the same as git switch or git checkout that switches
# branches while keeping the local changes in the working tree that do
# not interfere with the difference between the branches.

# The below is a more-or-less exact translation to shell of the C code
# for the default behaviour for git's push-to-checkout hook defined in
# the push_to_deploy() function in builtin/receive-pack.c.
#
# Note that the hook will be executed from the repository directory,
# not from the working tree, so if you want to perform operations on
# the working tree, you will have to adapt your code accordingly, e.g.
# by adding "cd .." or using relative paths.

if ! git update-index -q --ignore-submodules --refresh
then
	die "Up-to-date check failed"
fi

if ! git diff-files --quiet --ignore-submodules --
then
	die "Working directory has unstaged changes"
fi

# This is a rough translation of:
#
#   head_has_history() ? "HEAD" : EMPTY_TREE_SHA1_HEX
if git cat-file -e HEAD 2>/dev/null
then
	head=HEAD
else
	head=$(git hash-object -t tree --stdin </dev/null)
fi

if ! git diff-index --quiet --cached --ignore-submodules $head --
then
	die "Working directory has staged changes"
fi

if ! git read-tree -u -m "$commit"
then
	die "Could not update working tree to new HEAD"
fi

```

## .git/hooks/update.sample
Size: 3650 bytes | Est. tokens: 912

```text
#!/bin/sh
#
# An example hook script to block unannotated tags from entering.
# Called by "git receive-pack" with arguments: refname sha1-old sha1-new
#
# To enable this hook, rename this file to "update".
#
# Config
# ------
# hooks.allowunannotated
#   This boolean sets whether unannotated tags will be allowed into the
#   repository.  By default they won't be.
# hooks.allowdeletetag
#   This boolean sets whether deleting tags will be allowed in the
#   repository.  By default they won't be.
# hooks.allowmodifytag
#   This boolean sets whether a tag may be modified after creation. By default
#   it won't be.
# hooks.allowdeletebranch
#   This boolean sets whether deleting branches will be allowed in the
#   repository.  By default they won't be.
# hooks.denycreatebranch
#   This boolean sets whether remotely creating branches will be denied
#   in the repository.  By default this is allowed.
#

# --- Command line
refname="$1"
oldrev="$2"
newrev="$3"

# --- Safety check
if [ -z "$GIT_DIR" ]; then
	echo "Don't run this script from the command line." >&2
	echo " (if you want, you could supply GIT_DIR then run" >&2
	echo "  $0 <ref> <oldrev> <newrev>)" >&2
	exit 1
fi

if [ -z "$refname" -o -z "$oldrev" -o -z "$newrev" ]; then
	echo "usage: $0 <ref> <oldrev> <newrev>" >&2
	exit 1
fi

# --- Config
allowunannotated=$(git config --type=bool hooks.allowunannotated)
allowdeletebranch=$(git config --type=bool hooks.allowdeletebranch)
denycreatebranch=$(git config --type=bool hooks.denycreatebranch)
allowdeletetag=$(git config --type=bool hooks.allowdeletetag)
allowmodifytag=$(git config --type=bool hooks.allowmodifytag)

# check for no description
projectdesc=$(sed -e '1q' "$GIT_DIR/description")
case "$projectdesc" in
"Unnamed repository"* | "")
	echo "*** Project description file hasn't been set" >&2
	exit 1
	;;
esac

# --- Check types
# if $newrev is 0000...0000, it's a commit to delete a ref.
zero=$(git hash-object --stdin </dev/null | tr '[0-9a-f]' '0')
if [ "$newrev" = "$zero" ]; then
	newrev_type=delete
else
	newrev_type=$(git cat-file -t $newrev)
fi

case "$refname","$newrev_type" in
	refs/tags/*,commit)
		# un-annotated tag
		short_refname=${refname##refs/tags/}
		if [ "$allowunannotated" != "true" ]; then
			echo "*** The un-annotated tag, $short_refname, is not allowed in this repository" >&2
			echo "*** Use 'git tag [ -a | -s ]' for tags you want to propagate." >&2
			exit 1
		fi
		;;
	refs/tags/*,delete)
		# delete tag
		if [ "$allowdeletetag" != "true" ]; then
			echo "*** Deleting a tag is not allowed in this repository" >&2
			exit 1
		fi
		;;
	refs/tags/*,tag)
		# annotated tag
		if [ "$allowmodifytag" != "true" ] && git rev-parse $refname > /dev/null 2>&1
		then
			echo "*** Tag '$refname' already exists." >&2
			echo "*** Modifying a tag is not allowed in this repository." >&2
			exit 1
		fi
		;;
	refs/heads/*,commit)
		# branch
		if [ "$oldrev" = "$zero" -a "$denycreatebranch" = "true" ]; then
			echo "*** Creating a branch is not allowed in this repository" >&2
			exit 1
		fi
		;;
	refs/heads/*,delete)
		# delete branch
		if [ "$allowdeletebranch" != "true" ]; then
			echo "*** Deleting a branch is not allowed in this repository" >&2
			exit 1
		fi
		;;
	refs/remotes/*,commit)
		# tracking branch
		;;
	refs/remotes/*,delete)
		# delete tracking branch
		if [ "$allowdeletebranch" != "true" ]; then
			echo "*** Deleting a tracking branch is not allowed in this repository" >&2
			exit 1
		fi
		;;
	*)
		# Anything else (is there anything else?)
		echo "*** Update hook: unknown type of update to ref $refname of type $newrev_type" >&2
		exit 1
		;;
esac

# --- Finished
exit 0

```

## .git/index
Size: 1339 bytes | Est. tokens: 330

```text
DIRC      j�'�2��j�'�2��  �  p  ��          _rQW;�q��| ژ�I��$� .github/workflows/test.yml        j�$y���j�$y���  �  c  ��           AW�z�����)iB��~P�_DG' 
.gitignore        j�#Jpj�#Jp  �  3  ��          *�������N
�P����g�e LICENSE   j�#3y�cj�#3y�c  �  K  ��          L1,1B��_f���G����� 	README.md j�(4*a�j�(4*a�  �  �  ��          0\��g_���|H�`�ߓ�?��3 #__pycache__/ctxpack.cpython-312.pyc       j�'�#�~�j�'�#�~�  �  H  ��          6�7��qP	FX
aK��hAI���� 
ctxpack.py        j�#>Q#Fj�#>Q#F  �  =  ��          ,�^��T��7sA���9g< examples/sample.context.json      j�#:�gYj�#:�gY  �    ��          �{D�0�+���v�R�!�� examples/sample.context.md        j�'�$�j�'�$�  �  �  ��          ��C���/��C��L��_S�m pyproject.toml    j�$_�_.j�$_�_.  �  V  ��           }�U�N"�����tP�/c�� 
pytest.ini        j�$M(�m�j�$M(�m�  �  �  ��         P*�RhU�˓�y�h���
Bg ;tests/__pycache__/test_ctxpack.cpython-312-pytest-9.1.1.pyc       j�$K"��vj�$K"��v  �  /  ��          V���$��Z��ެ��ԋ� q� tests/test_ctxpack.py     TREE   � 12 4
捨�y V�Q�	*�N��[�tests 2 1
�������K������T;__pycache__ 1 0
ړ ��^����0���C�̜�.github 1 1
`�eZŐ	u������nworkflows 1 0
�ۡ�O9֨��2�,j:�5�examples 2 0
�7��^�B��-���O	l7z__pycache__ 1 0
s?���>��������ؤF�P��+s`3_�G�=�
```

## .git/info/exclude
Size: 240 bytes | Est. tokens: 60

```text
# git ls-files --others --exclude-from=.git/info/exclude
# Lines that start with '#' are comments.
# For a project mostly in C, the following would be a good set of
# exclude patterns (uncomment them if you want to use them):
# *.[oa]
# *~

```

## .git/logs/HEAD
Size: 1269 bytes | Est. tokens: 317

```text
0000000000000000000000000000000000000000 9050c6d6b82f98da7dba855b11b498f6a3ef06f9 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110147 +0000	clone: from https://github.com/billybox1926-jpg/ctxpack.git
9050c6d6b82f98da7dba855b11b498f6a3ef06f9 9050c6d6b82f98da7dba855b11b498f6a3ef06f9 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110147 +0000	checkout: moving from main to qwen-code-9e9a5a4b-551a-4e28-a096-b2cab196ebe1
9050c6d6b82f98da7dba855b11b498f6a3ef06f9 fe3c9822e0a1b556f81e64f59495531e9f6f78b0 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110227 +0000	commit: feat: initial v0.1.0 release of ctxpack
fe3c9822e0a1b556f81e64f59495531e9f6f78b0 47b34056a5ccb6c7130f7bac68112813bb76a3ef qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110508 +0000	commit: Add comprehensive pytest test suite
47b34056a5ccb6c7130f7bac68112813bb76a3ef 4e44d0c520495084def9b8ff660558823a61042d qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110560 +0000	commit: Update gitignore to exclude new configuration files
4e44d0c520495084def9b8ff660558823a61042d 97439fb73eaa36b98b572827f7c9c32aca1845a7 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787111437 +0000	commit: feat: upgrade to v0.2.0 with include/exclude patterns, custom output paths, and budget warnings

```

## .git/logs/refs/heads/main
Size: 206 bytes | Est. tokens: 51

```text
0000000000000000000000000000000000000000 9050c6d6b82f98da7dba855b11b498f6a3ef06f9 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110147 +0000	clone: from https://github.com/billybox1926-jpg/ctxpack.git

```

## .git/logs/refs/heads/qwen-code-9e9a5a4b-551a-4e28-a096-b2cab196ebe1
Size: 1012 bytes | Est. tokens: 253

```text
0000000000000000000000000000000000000000 9050c6d6b82f98da7dba855b11b498f6a3ef06f9 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110147 +0000	branch: Created from HEAD
9050c6d6b82f98da7dba855b11b498f6a3ef06f9 fe3c9822e0a1b556f81e64f59495531e9f6f78b0 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110227 +0000	commit: feat: initial v0.1.0 release of ctxpack
fe3c9822e0a1b556f81e64f59495531e9f6f78b0 47b34056a5ccb6c7130f7bac68112813bb76a3ef qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110508 +0000	commit: Add comprehensive pytest test suite
47b34056a5ccb6c7130f7bac68112813bb76a3ef 4e44d0c520495084def9b8ff660558823a61042d qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110560 +0000	commit: Update gitignore to exclude new configuration files
4e44d0c520495084def9b8ff660558823a61042d 97439fb73eaa36b98b572827f7c9c32aca1845a7 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787111437 +0000	commit: feat: upgrade to v0.2.0 with include/exclude patterns, custom output paths, and budget warnings

```

## .git/logs/refs/remotes/origin/HEAD
Size: 206 bytes | Est. tokens: 51

```text
0000000000000000000000000000000000000000 9050c6d6b82f98da7dba855b11b498f6a3ef06f9 qwen.ai[bot] <qwenlm-intl@service.alibaba.com> 1787110147 +0000	clone: from https://github.com/billybox1926-jpg/ctxpack.git

```

## .git/objects/05/91075ec1d054f5d4377341f6c4c40f1939673c
Size: 288 bytes | Est. tokens: 68

```text
x��AO�0�=��,���d��ūev�M�h�����������k�VU�e�g� �CBS�2���W]ʃ�t�Q���U��У��Q�����P�V���Y.�>�mZt£�ps���k|�ܭ�7QW�o����>�������^`�MW2��*Iݔ�5I+�Vߖm���T�H��f��r
�5j�I��� �A�BV�e�4�{�����DA�SE��;N��x��H�? ]e�o@I��b����~����b��#��,���A��=�O��iq\| ��~
```

## .git/objects/0e/cc9bc152966242c6c1051c13a4d1261d7570fe
Size: 250 bytes | Est. tokens: 59

```text
x+)JMU025f040031Q�K�,�L��/Je�uָ����͊�qf�S�	���>CU�x:���2,`?8��۷�~\K��ە�B&�$�����U/7��P��iYK|ڏ}����|���d�TQrIEAbr�^A%�g�~SE�N6������O]���� R+srR��ɛ���ܩ�������9s���T����e�e2����h��N���O>��	bHI1�=3�U�'���uz������W h�f�
```

## .git/objects/2a/bac6e71693e4f147e2e66e487dc90aa9467b58
Size: 3400 bytes | Est. tokens: 801

```text
x�Z�r����~�|��G�8���$�R[����.����]�X �"��y�S>#ߓ�/�t�ܰ[I�Z ���ӗ�==�*�+����u��Ѫm����H�T��U��AE�iw[��k5V���e���z<k�V���qW��Z֝b��U^d��y� _�Uө���i�j�>+�i7]��ڪ��Uk��u;��3�v�"�R��k��gO���<y�����yr�ꫳ�o�D}q||��?{���Y����g�bl%��U�#G���˧ϟ9�٘D��ޝ�~w������4�N��ӷ]����.�e
���|�����s����y7P��⺜G������Z����iſu&��V�{Vѡa�
I���x�Ǽ��.m�w�#��N~���_�Eڶ���~�1x��T3Y�>�O]g$��hp?�x�-�/y�������	̠ԁj��Z��B����Fu��T?����j�2=KWE7�AU�%b�V�tS�æ��EV��������|}�Y�$L��e���ݪ)�rn�b*��e޶����5�,nil��T�;z��U�~(��b�O�.I��t��Ibh�F�� 5{ڲ�t���d�? �,o��gdؾ�P�g?� .*�z�^����\��]\6 >}���("@y�X-��8#���ǡ
����8��/�_c;28�G�SG�U�B<S%�9������HlKj�m��8��N��M�-z+ �0�  lU�=�V�l�E4Ri�f~�Y��1J��2�L2��	����x}�?���e�;��Mג@�� 
v$s���8�	V�4K��=��A�Mהxiժ�3�BN���-t)M�p$]UU��
G�:oV���1W1H#r�rm�jy��itC��1�.������i��U��u��͞H�v{��"�(��FTE^���B#ey�����o����f�j�2��=����!f匈þA���(�6hLD�rK�?���"�`���m]�Ӽ+֎�h9����G��1X80i����Dq��V�������Y膝��P8�$�ɦ�)M��t�E�ޒ��*2�O�� ýn�>Fs����TO�����?k(��V�bZe������Ņ�)���9	�����U$�F��H=��Fơ�	aVB,DQU/�R;I�`'4��H�B0���BH�]UI�s�X{���,�<�h�:"a�>��4J#�6]���m�#�,[p�
G@����vd�/U?K{&��f��SBnJڵ�N�N�	5�#6��؝nG��/i*#.K�j�MS5�$B�X�S��� �43��o�����UIJ7��Dg� \.%�g���;}A��8U����DVE�[�š��W�P������Wߤ�5�졚VEApTV�X�Y&�!��h��4K�Ի��4ً P@�<�����wÏ�+U�`eAXoE3
�^c�м��	�bkĶ�1�V�*ϐ_�)�)��(��E�8�$y�w��'�,Yo�H?Y����� �l�e/��vZ��� �i���j`�;���
<cS��83Q:��mA��i
:�e���#\��@f�C��	�"@���И�۹�$\����rr>ok
9}�a�E��-��^���D�	�>Hd�>��#��X��D�h��h`�c��$��3߽(�@���%Nlr�B
'_�%
�|��UW�:��U�b��Z�'E���Ru{�n/d���׀��"��o	ɓ�U6��Ѝ�`t8T2jvx7E����>��v(��~�M�6�S*|�$�n��Z��Wq�8�vM��K�;��6�ř�UB�4�wzIQ��v*�@2c^D���1ו�>c���?L6��ؓ�D��h�~<����c�Q1�c�@=ʀ�F����Q���`V�\�p چd�d�r=j��v�r�_�^!��{��ќҬ�zeѼ��*�b�f��<��f��=�d�D�+���G��?�arq��^R��}�}�����w/�<:?;�p1��K�LN��a�iU��%��ᶥ�E�j'KOxˡ0i��s�\��#�C�a�M�o�����Zȗ+PV}z�h�u��
U�˴�Ϊ�r4�3�-.�����b7>�F�D������4�ϳ��
�����B~h�������Q
`�����ʼ;*�.���p�h<��X��Bޢ��Ytp��H��pzy�6H�"�@B��is�E}~�v��e�(7���b������sUO���������o�r��@�m��1�Y�?}�������o���m{p��!2�sh6Vy������S�ӻB?�y��i��7�f���0"üj��m5�#�!����nQ/��Zރ��$�b�G�����:�Y�z.=��w5���Ӯ.�m~�9�z���隇��́B��������`��/i��z�Q�L4v�%;]��T�����4A�/}�\��Ŵ�����6�ɛ���l���x������l�K ���@���	�̦�h�ʷqۭ=
�,��-59c���:�!Eط����)�i��yr���_KCҭ
��j�b?מ�*���r*��Bq�Z��Ї�V�ѥ���H���i�kx�IzI�/:i�����E�H��s�}1)!�����O]��A��9�^��&��42�7
B��BC�2��Gv��Ù��L��z�����_�ڙ;g�����=Dj�8�-Pʎ���;�&����}����{s�C�!���I���X޼�TUw8�h$[TN
M�I�,�ʶ�bZ=�NǮ�b@԰���B�IA����
n�����6o)(Xd�
^�3�|a �݈_:��9�;�!�I���vHKK:5���.%��d�M�j��4-���뽢�P�r��۽�w}�O�z�emГ���e�NܾC��x^!)���@��#T�M@Wɢ,�"�W�m�$�G6��n��]��3}������y����XY�r�4��������%����Gƶ<��������e!��F����G�|�D�yM����������%��֣�	���9b,
љ���'4�u!�(�����������Y|�]]�t���8Ͳ�G*i;�X-��CDZ����EV6�s�̈́���:$1����K�#*�0���>�s�喈��p�p����|F��/�CDN�1���h-#E��
�+aB��1�
 ���)��n]�	�*����&6���߇/;Ⱦ[��Y�{ 1��3��}��q�w��3���X0Ң��>�҅z��%n՝�mIEĂRZ�#?��+�M���،(��(z'd�I蛹T9P/Щ�����
ݪ�JZ�=���2���|��!f&�&D=Q��
��1��i�꓉�� =]{�䄒���$
I�&8$��e�D�K%�����
```

## .git/objects/31/2c3142a6845f66f8bea247ddd9ea0f81e49a12
Size: 1088 bytes | Est. tokens: 258

```text
x}U�n+5e����l�ҙ�U����R���[D�+t���|I��؃�I�,`�K$�X"��/ ���g&M	�n"�c?��8�LN�'�g�FwB~�
�u�Nf��,7&�&i��O�孪J���Y7#��/�j��sʭ*�L9�{fMV��XNyc��
�u8&uI�&�eY��0��ʧ4���;�T�BV���\�#�p
��\��ڊ�ys�:�[�ķP�i}��BH��
������&i��ID9"���tH�������Bi��ɼbRz�:v03����S��T�]�E[K�d����,"�^��z.�C���b�64�4�.�6���qn&�ʧB�F�K����?���-}�Ek�Zr�����=��Tp��x���8�����C9�����:q~
 �=[������jP����͒-RV�B3��j��~��.�y-=�E�u���e�V`f!��1�e!���������J��/v��~��*�b޶��	�V<k�*�����j��̀����Vze4-�$ӄ%��GEDx���UG����EL˔>n�5��2�����t(/˲\�� %״�q��1F%܋6o�(J�!�z�+T������%��|�߸�J�f-�EmJzw5Lv�C�X�� qX�h����ԗ�A�GL\`=��'2�>E�gViZ��Ҏ��7m6k� �}ɨzW~(kD�k�[&!�0���N�H-��AY�/�FW��F��qѳr)u�Pj$�m*є=J	��f�x"1��G4�Awtrz|||i�9��p9�a�al@����d�ڍg��'�!�7f�&��J��g!�@�Ŷ�;��)/�
֥�%�i�S���Ń�Jx�=I�(�w��:8_���]*�[�
k����<s9)~�p����k�0�zhb����a�Nj��:��qn�]܂ʲXi`@|%��:��������} x>twc{����Ϻ�ڒo:�É�������:�:t���X`�S���9�<�~o���OǛ�L�1p�f�|�Jp��ۼOxV�����r�V4����b�}�}��φ?)�m\M.._L/_����Xt�^�
z�n0�
```

## .git/objects/37/b8e571500946580d614bbf926841499ba5bb9d
Size: 4779 bytes | Est. tokens: 1127

```text
x�[�v�ȑ�k=E�=&�g&ggy�>G�e�6�ǒw��Q`�hJ�  mi�r�W�y��@^a���?��X��.L ]]U]]�ݞ�L=��߾��v��n��Y^���ZݶWU��NE;��f�ί�X��+]f��ߎ�֪֫j�V�U]-W�b��:/2]�<u'_���Ui}�J�F��E�L���}���J�\5���u���Y�(�WE>S�;���<zu���Y�����Gg�������������
�>y��(yu��CQ�E�eU�ȁ�x{����1ˎ�9����(99���?���ٻg����L$��y~|r����������[f�nG�/�W�e4��+����2_�@>��w�ɻ����E42H�n!�)_�o���{������n��:/ҦqHG5��Ǡ���Z]z��?���j�������K���숄����rWjW5��J-�B7���Z�Wi����>W�[��E�.ڝ<��J�d^���rPWU;Q��C5~��|�Nd�Q�pJ��D�O*_��U�&o�&&�%ItB�	��WVk�]g``�cA5
}��ַ��>|΁7�S�JI�Reyy9���b�m4Ti��鄢���.�ZL�,���雹�q�O^���+l#�w�'N�pZx��	�:R�"O��Xgz�
��i���{R#ݢ�{����f"�o��e��w����p�ŗy����
�|*���%?y�$����+�$f/6�LPb[V�N�U����Opl�{�32����g?���a뤇�51K�.��cz70�<MN[r0�<�Z/gM���:�[4p�ѝ��\�}�j�Mk�|h���_0%�d���xEv[<e���M�R���؁&�z���Y� �Y,�<�Z��6��!��17_
�Ő��L���2S%�� �u�s�h7
�Z�ȿVq���7����	�e��B�Wmz�ժ�sM�R+����ed:��k�D`�B��eE̚æn�!
j]L�?Re��!��olг�*�-����M��T�x��~����b�8?�w���Z�أ�H�݅�J�¾a���?i�n<�
n����c�K��!�~hP�ZEd�����km6�9	�4��!D�@Ǘ1�PLX����th�p�]�&���nB6{{���h�}�,�F
d'�P�K}�iQ��'�+��XmH�`���!�*k�S3OWz@"��e�\�臽�KB���c�����$�@��u�1�*#��	��J��*-��q8i��u�%H��i��+	�@���b�oճ	"��D�m��Z�R#d-��IS�}	jF��| ����V�%�o���<�S]�YT�
r+�����a��&�1.�5���*�g�,�^Oc
�����Κ�X���3(�/H�vzc�`6g�A�-�51�'��`�w_��xWg�Ap��?�9=rv���L��}!W����羮��ױ�nݴ���B�x�؉��C<!�����/��	m�n��I�52$���o��;�򃮯/��*;u���_��Q+�q	Q�w��-ӛ���Q2����W�Ŵj�ė�r 
L��NV�Q�@�΁��1$�4���6
y{
&m�k�Jo�
��r�f�X�7�c>�z0$�(SB��K x�:�o��Di�`m�v0D4N�Se�g�[,x
�Gfk��+�T�vX�lq�E����G���fx�]'��������FƛnM�-����e�R:�7e�f/�|�#����g���=e�9%oq��H?)(v�
@�b��/�N�:�©��iq���~U�P�r,>�!��H޾�m��m��r��=�\�,�d=��
rVnɕ���?���V��fp���y����*( ��'�c~��~��Ec3G�D2�K!H7�SZ�Y�D�y'1�|{�h���� GE��I��o������3d���/�2s>��h<�[�{ ���'��"����X��Y(���by��k�T���È���P�B��4����/��-���R�Z���8���ėÿE��n��m�0��l��	�R���D��V �M�En�#a(�����PF$�-��&�������1��m������r���f�n�e}2�8G7E�J�%XKf��R�7j2?vI#%�f	X!2}4v�5�s� �JŻ0D�r��,��,
1�V"�A���BA�M-u�,���=�Y��y��j�"�����0�A5��r��zy������'q�u� �v�Ϻ��m�����
Zcx
\�]o���`��z²�گY�v�O��y�4I8��@$�
e0NC���F%�G�L��x�*�̌��5��N �]d2�G��L2
"k�h�]k�J$#�d��o:�Z���D�?�����8����8yqxv�����?�E�֊)\ �g0��������jX�v �[
�g~�M-�n���A�"�PufKn��6ՃW�E�t���,csWy�8#!�3pqL���5e�˴�Ϊ��C��S���b���f�p腾6�Q�bU��պun��E
Dt8w���N� �!��F��@��S���xGL"t�������p$L h�G��wTgx�to�M?}��*̷������˟���������뽽�:#����j��:�YܢF�I%�!��:�Ѐ!��"=�>�⩖9
�,6�#�la琅���1�D&�0����t|�w��#��'��\�b��=�SDj�M�}���6P�5m�"�A��K>���#���y��H�g����n�:�xz[��Ǐ�&��x9�S@��J0*cM�_8�������O�!��W�n��H��|�2���8���ӷ'}s2���+2U52�Ȟ��D�`�3W!�n��)�$��� K�J �y�X�1�͝��٥7��ɢlg��� ʫ�$�
?m��SC7��}�\�ifV_]G��M���6Y.�{7��;]��[-�A�Ls����%&H��foR;��9o�U�@Me��0+�Ȥ嘪�tF
!D״<�s��l��Cǩ�
��c�L7ӭQ�����5�T���vSʷ�	.�>�E�n��v3�$;B�ԫ6Tͤ�ɨǊ�?ugM :�?$Gԟ>Q�/��
�)�y�ҍ�����=�������g�@�H�,h���(;�F{��zY���ʧ��Ƴ��
�Eԏ�P�`RXD2�����]����e��QT���I�tq�/�?��
��c���X\f�\��|��'�'DL>�Q��������p�ؚͮ��b#B�L
1Qo�fp��Y}�I��H�b�f�H�
�p_m��R/oN��,��9�T���ۣ�;˼iP�8���{��!���@{*}'�����s=W�Mx5��
�,N��(b:�����7�?��@���q�'�s#>��!9�	����=1+w��<�qw�펰Ř��1
�C x�(����f��FH�@>�F&A�P�����?KRO�D�Dq(:sJ�G#6��E�#�R��+�'��� �ym�{�?~��= ܿ�"��q����-'���a������ٿ���M�o�Qe�]Q`�C�ҷ3��PiA������ym��@([��nY�����~����ksފ���������b�Ė(M���kW�W��%
�F��e5!�cmt˰��T�k��j�����G(+s!�A�@����d����
G�b%�h_�t����1�g�Q(W��	ȧt[����M� �Dy�/骀�
��4�@�$ު�Eq�������1�O(9'a	���������;ABĈ�;�e �������<�2�Eˍq�~��w^oo�����5WT��(̈́�Y���(��] �u��q�C�dڹ��%)/����0�֟�Ņ�	�X������م�)X/ȺL�	���Ͻ���Q����z��w��|�BR�VƖc��W�'�䩋����Bҙ3牸�����|��ɗ�I�u椳��&�6	�S#�]t���e�|�,�~�G��@�p����<
��k�����"��m�<Iuͯ�|�Dk��hѝ�F�f)��<v��D���
C���ޢ/|��\ؼ>�K!� kr���&�M1��l��ѡ��
���Y�
�V�ͨ�Ҏ{���hK]�rDԭ�]����I'���9>�/�K��;��^���(�a���S���B�0W8c��0Z�~
ʸɋ����\��\�h��/jԬg����)N��ߑ�5-(Vhq��|��{��r�QFf�J�q<~2���Ɯ~W�Xߣ+�N1�kb��f�@rj�+띰�/�C�q��&���6��c�ڰm�[��E���ޮ�5=nH�0��}�O����rZD�rH5l3�����_
�]��3���fx����W:�~k��FcQ�⒖8pry����O�z��#\�i���ph��?�C�4��.��F�����s����Ɲ�k�j=J�@g�

��Oԓ�Q£(0����tYڣ�#�|}���C��:�Q\��bĕ\vl
�EO����t��6L�>�1�[���vi����8Ȩ���{B�\	}3׬��]+b���4B4��y��D���2�9�`J
�S	���MO�UڄŌ�!�|�A�_M��l	��Q�q�Uf���!	���K-��w�!v�1D��q�?��Q�mJ��$FD���~]��M�\��KqE
���p/%I���y�$����w��)�"
```

## .git/objects/37/ca166b2aaa59ae394bcc16d7d2436808a84909
Size: 189 bytes | Est. tokens: 44

```text
x+)JMU0�0f040031Q�K�,�L��/Je�uָ����͊�qf�S�	���>CU�x:���2,`?8��۷�~\K��ە�B&�$�����U/7��P��iYK|ڏ}����|���d�TQrIEAbr�^A%�֮c��&?����Y�G�I��n�&@��Z��[��Z�pN�|圸�N�t'N^�ϙc�X ��J
```

## .git/objects/41/a054eab13c5c20fa5ad2cdbeacb49c8f8edd3a
Size: 9679 bytes | Est. tokens: 2289

```text
x�|kp׹�.�x?H$H��|�J-��˶lJ$e�A�"��,� vI���]Z"&T�S�jE�iE]�	��N�%�g҆���H��֝��,D�w�ު�۩tJY�V~��w��x��t)|��9���ٳ�|��F���=O��M�{��J�u}�w����~�7�Ej��BS�
���)��t�t?MR]����~=I�~���~I��FH���1s���8��������ƙ�휹�q��,?���������f��2��M��E�|	��� �&�4rEP_��n�?(�ڲA3�rW
t�V�ւ�ds�g����� �*�?/�{I;;��b&���J(��J%|1����*�z!%��F���>u��� �<Lg-_�n��Bmͺ�:��b����6�!�'���4B=�m|���6��6l��-#[(J0�(��g�7LS��I���c
I�ƃ���m����GB�̓ϳ?m����Btl\b	��Dx����s�����xP�������Xx(��=C�?,F#�)s��������}���B F1��p 7:
��J/� � �!�8�a�xK�'C ���P��Xx����!H.F��Ѡ(B�M�� ��a�}�0B4*)F��&�H�}�2BN��i 7�8%e�b6�����0֯���vZ(�0���[�+��?ө5OSS:	֟z
��\.��~�WH�1�����^*�j;%�u4u����.��R�J�v5�H	b`��L���z4��P42bᥳ��
�a��/�EI�+���0!
6���V̰f�\82��3*���ζ�G�{�;�:��v(F���Da�)Y�(t�X:.��q)���B
<�bSG�u�Ѓ"N-˲��Z.F��!ߢ
l|R�!���F�n5�D�4u�ē�nK�l�>�6�,��I�7e�Z�1W�U��K��
&�U�r�Yl[)��1y}2�z;�=U�7�ڳj����?X�6������E{q���Z5��#���VM����HGo��"C��t�T�y/�Ֆ6��� <�h8�_
�Np|(��
E�,��L���n����3s���8;���\W�[�R��;�zO���=ݐ{J��!�  �X�[z�e6����
/�f�v?��Xqn��V��8aa�v���,Ƹqر��4�X/�W=�U�8��6�@_�g�]��čM]��P�+�?m44���ѹvq��t�Z�H����Q`}J�խ�c}��1^�9�bX��<�{��]�3/�Z�� #����aSg  ,,��p���DXI���H��cQnb�I�����1������I����=26�G���G.d��!��c~d��z%�؏,}&�D?7����$�$ɖ��:�:�A �n��Y���ui;�@[oG���XG�t��9ѡ2f*lB������U�-�8k�18������DX�Ђ��?���A���T���Y+�!6t�Ed��C�����p�L�l�N��!�`�Z5R��ٽs�抹͉�i�wnob8mv��K��f+�*��=�b�J������R�������@h��\a�����]��"�\ڸT�q���yl)��XvlH:6̅�Ɏ
)G�"�i�w�I[�]���ewy��i��E�{lk���F���D��R����|z�Io�\�=�bش�=���ˎ�Gb<ڝڊ{�w�� ���F��pPgR�?�0����2��m(�Oz��n8#��<{qٝ4������\)��4���Oも���,Г�>������)�g���x���Ze���C����`=�f���YN1y}fEq��8_�d�6�=���t3�Aп���%`"�#Q�o�(M��X��$sKL��/�kjR�Wb��M/7�t~�Aj8�J�y(o�Ymԭg�N�aω��8, ��FA�*R�3�`�� (z�R1�I����^E�qj{T8�/�O� �����s/Y7L���|�ۗ�=+�L�����������ŉ��R��"��!���LuPp�d�/��.v�`�F�z8�;��ٖ�l�?��-y�Y�Lz���d���7Y�+�:�,>;cX�9����g�cng�V�v��m�aL�)p���p�0km�R�a�ْPVrB��r�7�����:E�-5�O�HO=HO�uS�<)��
 �2�d��z���:����u߰���V>}�P;�g���ڐ�����(����!^A�
F#lf�Z2��
(���}>F�	J����U�A10×ԥ�+��HT�~s�r�ng�Nu<��`�W �8b�E�\�V&��s�KVv��KZ}K֭�Ӷ�k{��nh������rng�I��ٚ��]�
���J٫aaD)'(�����З p,l$�������k��3��ɀj\���7�?������J�>������c��ʆ.�����9R���O��ǂ��(��B �D�̈�"���*
<��ODKl����y�
��۾�׮��lu2SG���m�С����wN�LO�`Qæ�r�`!m��3������4(�����H��r�*ͷL�fAKDWSSC��BO�� ����V�tֲ*֞,��)=g��aD���!�Y���߂���E:kqYc;N�`q��Y\S��"Q�S8�!�ȭ���A�*�ݱ�s�do��AG���r�Ա[bfv`R�E��<5�Χ!�.QA�������A�����
}�gQ����`��b�^��u������@Ǚ���ޮ��^�MMRL��1^qk;C4����}��R� i�	�f�f�V��*e4/��E���cN��%N@�-?M\�lo�q��eSE�T�d�Lմ$M-�[Wu&�6H�M^���7���E�3������tY�3���ٽ_��O;\��^9;+&N/��9�r<{{�]zc��]o�A��z���]����V
�PvmJ��ͻ䢭��[�����Gb��'[�;�R�lq�>���,��g8�7�y^���	4Z��Sd8P��M)��J�5z�X����l�!
4'���*�9i����zZO1S�Y�&�h8SP4l#���H3����`��[��IY�TH���5�`]miTq�TQq#��)h2bSZ���>�C����V��-n���n�[m�����;e/l���@��Ũm�����T���m��6N�nvna�u��0�a��.N�&u+;� �-{NGG��G�m�r�C��H���q*3@� �v�/���wk�Ɋ�)@��R��������\d��B
-߇v ��9��0]7٣R�͡/�K���.�?����d��:�j��?�dpT��@QD��4�p%v��KD	�Տ�>����
s^�Od���p�/#8�`��U�=���s�SKv$
ؿQ�̐AFT,8�j��zp4��JThN1#�0�-�ױ�>D�Ȗ�W�\,���@Ʀ�� �Gq�t�ʖ�a�д��47Θf+����xf/��<c��S1c���i[)�074O��o����{����+����u��{ō�t�TB���u׌��e53�Ҫ9�z�LǊ�.�q�Tny^n{)�>�.���Ә8���:s(]��6��/)_.iH�4$ڗJ|�%;�%;�JZg��e���$�<U隆
�~gt�fG�f�JÎ��K
Ϥ��X5��	�dу2�S�ZF�v��η�/w'˛��S�ִ�\��0�c`�⥌��Ƨ����3���xG�	�=���
�8��Ī��1�J�W��qoc�&�� ��ey�PH��
�𺧘����11�ɦ�q3�#�'�{PJ��cH/�5Ā�NY���VR�uʖ�u��'�C���c��q�q��sz�u��Y0��Q۵�@���g����F	�'3^�5v�O���@uT��3 #
RF�T_��=A\�"��0cc<����ذw!����y����E���M �P4a)�A����Q8e���A�����s�E�C�0���%����)�	K����I�,���Ҹ�?V�c���6�n4��Аh����_Ӕ\�}�k�=��w�cw����!����h� ݫ�} n�c۬V�������m}��@inom�Ԯ�Z�b�2ˁ��'��R.����@� �L�J��@T�>7���cͬ*��G"���YliCΥ�[~,���FF�XGx~<@�mĶ��||�I̹v�B�������M��-�v/Uwˌ7]�?�,�;}��1ݑvMw~Z���S)W���<c�y����&�|�֒��\;v��\c�^���f�%�앎��
Ɋ普tQ�\����..[���%���6Vf��r��jn��(�,o}⥛f�+j�D�\�Mn	$+3]+�s}�X�Jö���0�^ٺoq��֎�.ٳ9iߒ�胚���^�/eođ��k�J�mOڷ�����\��}��ruK�pT.��F=CqF���m�
��3�[i����{zp4a;r唗w(p�3S��Np�ҐU�4L`	Y&\_�J���[��)����	�q�������J����mS�9;�����SHA��'>[���g��-�>]�'W���W�r�܅rN;PhJc�C�Cd�cAa��^���	i|B��<
�-~P�s���3�P1���28 �Ǿ�ЯƊ��5��\����/�c���t��DwW����}l�wrp*�Q=R9��' <ρ�D����퍎���y�f9�Yt,�<��b	�+�onn��X��Ō�� �c<��yTˏ��������n	��@.ݔ�&`@�K8�x��W�#�&��;����\�bt�u^���� (z�p�
G�Kx��$O�}f$:�	W[�%t!�W�^��Sh�K���@��ץ�ִ�j��GGo}�[��:�]67����|g�\�$���Z�t�;e.K���W�rY<e�J3���^>���S�{���Z�6�&�7����e���)�h��9.�l��)y�vy��O��+��W�`�<��$�I�}iw];z��mK�h��|��y���~�\��=s۪
�����j�䒭Jf��Q��jX�St³v�א��:�'}�Q��M@g�#C�ƄtCTHw�=0�#��
R���yX!猚�0Md3��5\�]�� �)`'�z!G����e��a��tkN@�d͒��[��d���!�@\ǹ�L�b�,���.*���E�#8BՃ[�	� `��װ.@Gv≴�s@�w�Q�$��S�R�m�q��ѷ�����ڴwӃ�[��e)�>(��,�꠼�Nݴ�k���I7l���M6�Ko��љ�g#O/m؛��MXn>��ft8a=x�"�"�q�*2���
D�6Ilm+�+%Y�!k�LY��
L�u�D}:ϯ��@���L�^q%ibM[a���g�p�9�\��b"�zJ���tg"�:p��u��,�EGh�4e�i�\�@Sy�Y}yMi�N����ӳ��ֵ/��sE�0 lt$u�M\	ܻ�3iϹ��R��2B�y�H���<��CEܰ�w��ud.�,�[���\�d��:����H,�#��/��~b�'
V�8�p��.��3���7C�f.\���@���< ��PkGޝ��{:>޻�:+��������J�> ���ğ?�����W�Zޗ���/ps��/ޫ�7� :�y�!��y*T���>�e�!:�8:cU�E�C�<��B �S�;����X
 �@G>�$���_�����Ƚ��[���+�����o�Xz�K��_A��#Ȣ��^��d��7 �}Қ�x�~�������&�:t��EU׎ck}wK1��OMD��9�U>�s���g��^uSĶ|æ����U<p �ܪ:�����.!��ӳ-lL�v��`L��sE�(e�5�$��Wi bN�"��N��(f]rۓ��2��5��U0�Q'�����>�}��B ywD��U��X��S��&�:~�(+�����
��DN�1�(��pH"kM�7Ͷw�Y(��@+�����u{��.�<K��+o���%�KK���{H��%�%ϑ��|,p5$�4&�^���#�*Eu��@t&}D7}����m�o�ٹMI��y׶iq;93���S��Xdku�� ��Mo�{{��D�O�rm�l}*�lW����h^\صX�дx`Q��s1|[���S̑�i��~p���n���ɝ�>	�;�����ֳ)�?��(�u{�ّ6y�<wM�+f��<�2��L�=���54k���}�MbO�w��~�.g@���CN?DA}���3�2k��ؼ#9��g�]��"%�1��M��X.g�e�zY��\�-w�V�FJrX�8�}��k��1:) }����>���L:�Ɠ��v<��3�� �u0X3Nl.��jA����9�XX�'�~S�sǶ��Z�A�	�޺h_�@"� �8��Qh1{~���
; �k��bq�kjj qg10d 4�E@�(�"x�.��J��od&�,V��B�lcD����ęf�(�LābU
zt�+�K�S�s4��c���\�Z̬�/�Ɗ��(�P��xV�aC�Kч.r�_a�[���M���³X�ъ�� 7r\)�+( ˘�/Eqj�i�K���sCdm6Z��<l��">��%��sh��aI�;�VF���G�����}���2��~AYX�C��1MwYJy*o�_�O{7��e���M��<�댫v���K����^-�FK�bd��<˶
I���1���5Is�ܷM��&e~8Ԭb��f��gn���H��⍉��|:e����g��8�C����a-��U|=�c05�r�I�ӎ�E[���u�aLl����8�uW�B���������8�Hj�X+ͥ�v�S�'�f�R�u�6F
y��\Jh�b��z"m�''ꕥm�sc#Я�jr�pbt!��U{�n=^��<���fNsL�
��k
<���g�E6>�mdq��
��S4r�<������3��(���홳g��̅ǫ��k�Yڬ=-g!�4���1� w}Z-��! w$\S��v6	���m6�
n_C�9����|X��N�Ь W^�=n���uĽ;n9��
�d;��\�{��0���g�q�0J�u���\q+<�M{2�u�$���`[p�F)���j��h�\��s�*�h��'o6�⎵zĚ:纺gT�p�'�0�������tQ��A�W��
#�q�AFDx�$	����%�|W�I$�pz� ���5�_�Y��O�1��s��������q� ęg������� v
���"|F�ߖ�#N��A=��o�@�xZ������QC�
��!V ��(V�N
��D�bV+e� ���:�}=G �Iq����6�+�p{N�?�h�:ۚ�A��L�̫3ц���(���X�SC�(���H��F@e�-֣Û�¿�� �Q�+>�|
 Ũ����b��Y�����Ib�]�:�v7�C���	����H�"��Y�I�4|��?J
�G��5�D$8��;Wl%��sU	>e۶��%W��*����=3}��}�܂�W�U.���
,mMw��,7�۸{��F��kO�����O�S��ON�oZ�o�[�:��p~߹���M7�>�:Z���G6F��b
��N��͵Is�B���~tt��3��y[L�Yb�&[�̿�p������ʭG���{�ciKѵ�+��])KM�y�L��S��˽�/ɣ��5�͞�k��,�G�x��9��]�<��=-3��:�S.�-��䒭��ò���~V�,�_��i��+�TOw�L}i��ܳ���5ӇҌ��c���u�t�X��es{�&��ۓ��P\>wv�HbJ�|:Y��t�}ƶ�x��'U�e޻оؼT����cH1�Ҍc��H2����f��|�}�w}��R�Yy ��rr�u��H1�:gw��rft���٭��&��~Ƹ�fC˂���/�Ru�课�c"�-�ۖ�Õ����5��>{eM�_ +�SjG�ʞhN�������N����=S��l��y�-F���}ݕ3+oe ��9-~��GQ����F{Ni���"���A�9���*҄9;-D�X�*�|��
Z��i��-Js-r
)W�
Zz�Zf�V�����\孪�h��,�n�*�wC
W�{�p�)��i�����5�|��0��02�uW�͌�ugٷ��ֆ�h�D[w��0C+��Ъy�Z��.);�ZY�!O=c�Z��fR(��b��O�# wY0Y.�qNY����uǞ�X��U��Ywa�*��<_р��������;!�X�ъ���P�0�0��#¡��@��������s=vr�)�='@�����c:AR��Gh$��G/_���͙��*!�^��j���e��>8�d�I��&S(������9����#��,������"��5�ȿ��,
!��g�tK���f�ɸ?b;דѾ� q�~��E
�@�¸�� � �}1{s���4�
���S�T����'6��2���n�C�6x|P���k�,�ٯm�Yj�H�9��/�@�똏Ug\U��8�@m�@��}�!\d��?���W_�C0�"���	Cc�M�[Aq9�H-D~Z�^�Q��K �"�(v�b����S.a	�n!����{�)VB�E�t!(�sq�"�� ���j��$��
�gP��QX�Fgõ�
φ�2sCT���Ƅ	��~�!��ij�Q��hL:ӥ�_�uN�t'hM%ˮMIצ��ی�ڴ��>|��z�ds�d�Q~:(�l^*�Ϥ��e�T����ŷ�A;M������
��9�nܟz�O�R>yJ�?��������}��ܹ[�b{���l嫏Wn��/RϿ��?�mړ���/ݩ�=���l���څg��/d�䪲Ohs-۪���%[�t;�U�5�⒧����B㯶~�5�v*���t��=+�u��y�R��w+���n��%u,���nO1�+^6Q�xcɻ���"�k�����s�=����H��S�-�ʚ�j��0)s�	`Zy�1��u�k��n�b@lL8�6*�@�����:�A�NJ�[  bR�c?ܼ ���j����_��KV�6� �g��C@{'�f %��a���G  ��8ibCI<�j����:/�A����	+N#@a���U?l�/@(	�(��>�����f�)��S��)e���|JY�G��~E�L���^��iO#��
2�J�U�T�S��;p|�x�����v�r�$sxLi窧�.��V)Hď|${���{��KWw8iל{��$q�$
$Yl|����JW)H}$E���$+��"��!����C�[m���s@�D�CLV�6z��$�0ϼ������t�i��G�$+���Ͼ��;��
�C#� h��*��o���U
��0zHn�ݖ>i��{OˇN'��<���}n�V,�~%�z��$�0$�_��W�6�h�\_��f�*�y$��$�_:����<���MnګaC��ch�A�M���/^���_�B7�<�)�>����c�n'lW������(�s
```

## .git/objects/47/b34056a5ccb6c7130f7bac68112813bb76a3ef
Size: 715 bytes | Est. tokens: 170

```text
x�TM��6�Y�bnIS�k��/!Z(���TE�$���C{���(ۋ�st����{o��~�P�Z��H`�%k}�u�Y����Jou�ܔ�\��\m�f��-[.F�	��և�j�KU֛Ͷݗ�}n7���f�.��n�ݾ^*I����[(�o��?��Wv�'����l4/�5���B��������~[�)a�G*�h��g͙i�
G���.�9��O�}��2*}Z�W��i}���������X�69-�;(���Vba�A�kM���9����˼P�}���t(%�4?r�W�k,Sck��J��n�H֜�>,:#O�>} �?c��ojT���N�h�ݓҒ�%	�y�Ps��Ƈ���}����8mSñ���A���]QíJV^��H�(~x@�01qF<�r_����V���#��n2'�r�Kρg�|���7���4@Hv0���B>�?���*�Ã
�H��FQr�2D`�~�c��U�Qm�����sOAR�41 Z>d�:�1G�Ɲ!
�`��h�D{���(z4(,
�S  �2�uj:�j�8〛��7��)R��� ��c�`�
��_\E=�q �̊@)L&���
�n������,�I��܀�tk�6Y�0΀��s�����dF02��{^�<�$c��Ɋ��6`j������z�h>w~~[PkU��ꄻ����&����	��é����	��
```

## .git/objects/49/752f82788fb9062bff008775f0bdaf65a66cf0
Size: 3489 bytes | Est. tokens: 828

```text
x�Z�r����~�|���K�+�*I��֥$*��fA�bv&@ ��5C�B�������9�=7��V%������{z������<��7����*/�t�^��nQ���(L��:�^��:յ.3]N��Y��jt]��j\7ղ�C]��"�M�K����N�ͼN�V��Y�L���~��V�}�Z�֮�����[��2�^�s08={���7�ɣ��O�Γ�_��x�&���c7��鋗�ϒ'Ͼ9�T��|^V����/�<{�@�1�
^�=��<�ӛ�/h���Ve�o�>���] �,={������w���K��n���u9�����O-/�|����g�ɷ����Eth����!&��)��٥
?�?��Ky��)N��m�Q]��s�~�T3ٗ^>㡮3�T]4��?���<����t����jP�@��y�fy�[U�
t��EZ����#u�V������*��P�w�)�aSU݉"����������a>���*2Wl2^Ӈ��nՔy9�{1
���2o[��d�
C���\���j�wG����}]����%	�N:I̃�H�^ f[V�N�U����{��������iv5~���b����5Kn������d��7ɛ�<����3�!�_������S����ݑ�!<Ҝ:r�o��*���-�k�#�-�]���F�t=��7y��!���9�V�Aۓh���_E#��j�7�U
��*/�a���'��ayy=��4G0%Iˌ9� �M�A�� 
8�5�Yl��V��J��{�l�4�_�E�*���G��;�9t��J�;�IWUU8'z�^�Λ$0㘫8H�s�rm�jq9�itE��1^�.���b��i��U��q��
O$d˞WFyr܈����K�@=^h�,o����kմ���T�Z&�����:�yA0gD�M�OTD>��@�"���@� ��ˣҷu�O�X����1�|�'��Iщ"Z��5���6��6�A*S	#'	��+�E~�
����M���Sy��b��I�a=�i/�!F0e��������KJ����JY�n3�p;�pH���6�E�~QgNSº�Q����B7 �p�w�[��Nђ�L�ZΛ�.��O��E�v94@�u����8Q�����Y��j5_(�Uv���5]�
S5eaBx1�Hp{;��P���H�/FBB���i4���&����U�%���3?�YZHa��=*�D�`�U���kN�j6�o��n4�>B�V!�i�F$�n�f�'��'�G���n8BxNh4�#C�A���$P�,�xB)���Zg'�aB
��=J�N��K),h)�&�`NB�j��i'J�"��,���f&��۩F	~Ə�*I�F���6�+��Y?'�N߃P�4�)X�I^��@i�*�C�\��[�9�3L�O;_�}�ל�մ*
��eU�%�gbR!����K��K�9X:�A��)���I����Y�!sïd+U�`gIE^�fp������@A�`���3f=@�*}_�q;EH#�Y��>����K�׍��D8Qg�z��A�Y��'�L���<�R�V�ь��H�L��0މ�$v��$�ə�Щ��&������R^I�´ �����=;��q�yD��;7�ʄ1�zib19��E���4=QOw������ 9¾ټpv�����H�����{#�ю�f
��[O}�"�����8n���
5�|����V]��x�A�5�k����*K�퉺��/�	�n��T�KP�\����n��
��Jf
�'0S�{��Y��O��a9��@'��`;T�Z�6�q�K��i�IWu)����l�[>�Q�uH2y���5�n'Rr$C1��E��=�0]����.��d�w���H(��G[���`��(�����a�k$���e2�-�`e�e
C@D۠uo׃W����qCBx���-2JsB�V�E�P�Q����y ���{x	.�����%������X7�8�k/�f��������������������%&|&'RI1ɴ��`��u��)r9v�h�Q om��o!����yxN!��͌��s���
�����Mh�}$.�u��b�is�U7�������rn|V����ci�!�S��	7
�g�SC21:�'�����V�{=ݿ끣��y9-V�ywT��0���}��xܛbj>(�0���g����#�_|L������,���
�OCX#�(�󳶋%^�r���[��	_La<r6�y��=��������L��6��v��y�i��|�Ļw���o�����=����	c���Vyɍ����
S�؛B?�y��i��7
b�f_aDy� ��fshG�S8lqU��6(�^^�|AI�ń�"
���?[�d���hP�ԀS`��]+6L�-�߹�Z�Y�i����́@�6[*�w?��;���;�!+����t�F\�wC��[�}@c�1r!JӿS�1�`{�@�D��fG�4���
�Oo�a�6� �yo�^�Ah4pP!����'�ݺУ�Ȥ-E�)jrS[8F�;��4���m�6�4oN�7�iJ�����������9��a$��
#�P���u;����lt��}$!�q��?�@�^� N?d~�8bх[7��FF�F�汿�.�SGlp��ĝ�ג��;Z�
�M���ЊL�w4ܝ��E�pf|#Sw��!�!���_�ڕ;W������V�E�|�[ ����;x�����@��[�b�7t�~':�c�����X���TUw8�h$,*4^�&ϤAHe��2��x'c��C1�@�0�p��B�INߗ���
��o�m^琳�J�t�8��� �v���g�����&����A-m��,x.6v�/v��J��<�Pk�o�i�G4.X�H��so��_��>�V�P�,k����E4t���m�c��b?���kn
)���;w�A�W�m�$�G6��n�]�f������z�݅�]����m*��;�����%����GF�8<��ً�����*���H����f�Z"˼��h4C&���z�����0��(zler��@t&�j4�)�^}����M�\�пo��,�׮��:��[�fY�ǑJ�;V�%���迬p�M�k3!j-�Q<~1��aD�/tQ��bε�1\>1��p��؂��C��*=��i��`�FkN(RE��4��3oଭ!��"~`�ֵ� ��.?��؜����/;H�[,�Y�{ Q�
g6��L��z���H-���DP�N�TK�<Hp�����mQE�A)-쑟̠�t��6�jأ3�0:�\荐�&�1s�r���SAu�	�7t��or�5[��6e"���)�C�L�Mz�if?�@��
��G�����=Z2B���HL

I�&8$��e�D�K���c@o�
```

## .git/objects/4e/44d0c520495084def9b8ff660558823a61042d
Size: 335 bytes | Est. tokens: 79

```text
x���R� E]�����ɃYX�~�KW��:	�@$d/���k�BvMsO��h?6B��ED�5b�IT�ٚ���,d��᪒U�jQQ)و�\�R���U��֪�R��
u�b��R�Ƃ�s�|��=�������2�b3Q�YM9�V��\����J!��%O��۴o�����h0�6���@=�A��!p��]c�9`��Ac{�����!��Cc ��p&�3���k�2%uB�-sepO�����i��W�W�Gc0�B6m��m��{ϓl嬣`"�8`졳�]K0��O�	�����_Q��K�@X\Xׂ���9���_rS����8
```

## .git/objects/57/ef7a9be3dcff8b296942a3c87e50915f444727
Size: 78 bytes | Est. tokens: 18

```text
xK��OR03eHHH�RVp��K�L/-J,���SH�KQH��+I�(QH��I-��K.��L��/J��
������󸀺���
```

## .git/objects/60/e0655a1ec59017097507ab99adf312bff36e07
Size: 52 bytes | Est. tokens: 12

```text
x+)JMU06c01 ����촜��b�+,������b��[:YV�L��  Y
```

## .git/objects/6d/4328d42586e1463a024199734260c81eabcef3
Size: 169 bytes | Est. tokens: 40

```text
xe�M
�0�]�S�`"=��;�EōHh~��&/4ii<���s1����P�j_m
rHQ�$Zo�#裱�����H��s�d'{�9���t���Pn}�r�B (H�f3���� T��}��4�+˨�������ҿN%���H���hU��[�u�ۈ��K?Y��y�E�
```

## .git/objects/72/51573ba47182a57c00da980fd84980bf24b708
Size: 298 bytes | Est. tokens: 70

```text
x�Q�N�0䜯Uqiy��z冀[U!']���1^;P��;��RB��zfgf7U�V�]i���Ď���e��X��J]/�KL��Jc��y����̟�⹭8��e�f�+����X�agC�X����U��.$Z�e�EG�UT�·7��2�:��l0+�(������|v�_Z�&�E�������
�'�7�g�O��6��6��F츓�2sޔ�7�w�+��1z!o5;�4��!=']+�l�\�#7{/��2PyNoV�)���!�����=�{����g� ���1�;
```

## .git/objects/73/3f0e81e8e13eb2e3c9e117df1d93e3c5d8a408
Size: 68 bytes | Est. tokens: 17

```text
x+)JMU05d040031QH.�(HL��K.�,����564�+�Lf��*=�a���M	�O>�f��� Q��
```

## .git/objects/7b/1244b730f52bb59e08a67605a80f5287219987
Size: 256 bytes | Est. tokens: 61

```text
x���N�@p��#\�d�R��p3=�}`w�b�?YS�/Eۛi<�a��}�t��Uvw�⃯��e:0�L�Y
5��mp��*�9C��SH��{'�<���Z�
�t�K !@|�+�o�'�Z/،<-|aٳDv{�}�Y�/ ��: ��bBڴ6%��~䝳9DQ'��
y����6a �;1Ɍg�5C�i
r^�QJ�7�~z��}m|G�����Z�o�Ki�/9[�� ��T�,>= I�#K������
```

## .git/objects/7d/d55e4e36ddb5dc317483e80b2103c9988399ec
Size: 58185 bytes | Est. tokens: 1837
*⚠️ Truncated to fit token budget*

```text
x콉w�y'
B���ᾯ�H,D�4z��H� � ��`/�@�@7�� � �I�xI"9�(�3qO��Ll�vl�>Ǌ�H����.�%�����%����w�[��X$JIΙyo��~w���|�]�::��^_�S__Rn�r�&#�F{:�3o�3�8'̔���̸�Ȥ'���t�Fw��Ǔ�f�H�b�Sq3�h��;��/��u���B����55��@:72�d:�̥3�F.}�Le
�V�4�5��T|�����	�H��#��e�R1U~:c�'�9T���p�\Gy�Q�Z'GR���O�6
�7`Dgs��]�3����F���p\�~�Ms�+���A��F�9Ises��f��)nG]v:<:�vO��"�Qsx����CD�#��������vL��i<!^<�E&ѩ�x�ό�G�I�Ȉ�O�nԍe�)G]G�p?�d:F�&�ٺxԡyS�ȍ�'�l����n�;}�{`���{�t�	M���gq��=y�N�Aræ�Hf��Fʜ1P�Drd
r�L��Y`�q:O&f
RL��E��.�Tܒ4�
f-7C��u�sΜHO�Fz<kaË�.L�
3��$U�(sa=U�Z�E��f�-p��ɬ��FLcJ5>����%������� R3�h��H�F��T���v��1.���΁������+��~q^��
{<�@<
��P<�G#�������C�@��Lx�pYY4I�F�ʉH2Ui��h.7�mt���ѩ(�k�M���Fӷ�a_�569��B6���,QGoA3f��Hdݣf$�uߜ1S���6Ñ��?�jh�F\~�rE<�+�E��p����ye��i�}KP�>O�+1(Ӑ�,o���D$7mf���f��(�@@wM�`rLGY�֧�HDƳ�Ac#��h�%��b��l,��T2%�(�uB��
�R�	�G�~M�O� ��JV̨,ȹ�*�'����/N���;299>�uMdG겑��q�V���ũ�����+? �H����r���_eb� C�*�"���)� �P��1af�0oF.��C�F�K�6�29n�\�
@FR�hz
����,g �F*�r�63i#��䦲F$�m$��)j[$%e@Y3IZ1�
Ʉ�"�t��'j[gv��,�Oϰo��f�
�r$kteqS*��X�Z�Ss��"�r�[O~8��:�YWvԕ5sS�!�5;+�!�i�d$�5
��w����2Y��ˌ���y9�u�pV�Y8�C�@83V�Xq�{�Yq�9�h��["3�l��%^�o��
;�yU�vp ��N�A*�H�L#����ͯU\T��M���/� 7�����%���.%_�b		�?�|!)��LHĿ�|�yG�*7SL�e�&��"�^9b���5�t"��Ǔ�*���Z�ɇ�4�J�u2���R�F4�>-nF04F�8q��8)j�	&f�ƀ2���g'`�
�+{E��̉���5��OG2�	^Z���
wwt�`D�����Q�u_�ZUW�r�����]ԌF��=YY��FP�u3k8�U k'���4��5��(TQ�ZZT2i�F�uà-kħ&Ǔ�.B�,H����DWA}e����U�R�(3��L�J%o���"x��+F�P�����V���(SUm9�3:޿e�>zs�jt";�Nq��a�&"�b��}K����X��Sٌ�8r8�`��v�rM*<ɤ .Y�u�iol�4S�&�w�#�)���]?�^e�O�lDaR9��@%�v[�pW�A��� e'1��Έ�9��R:�9�C��L$q���cwV`�1.�R�"�50��Me`�s���U��X�8ti�B�d��������MNY�M1\fe
3`���@�eY-��&�L��YL���/|�Ӵ�h֘��rZ�s�r<�59�N�8أVsꦔ9c�~�$Y��B�Qw\D�;xJS灻��Sff�.�ΜU���	aƬ�eQM���?_	�L�U��F)?,-V����k=w����;����Ȉp� �����s砇��t�<���*�v{(#ҙ�Z���X®XJ�Ɠ��Le�&'��iU��*7K�*��T֡\�����(ʹ8E:IQ���x[�� U����y��+q�9Of���ޗ1s�p7^�sx��H�ÜƤ�Θ7��0�'��z/�79�*��hլt�]�\�8���3g���ŏG0��TWU1;5�3g�<�­{�%�DI����.���t��B���p��N���j���z��8vGE���cvs$(kQ���CU�z0Ǔ�%t�hKYa�Z$rv�u���ƔQ�F%Fk
g�H�+X�sI�u�49�R�y�q*���� �d���Ք�N�nA2�2naE���}�(��K�3A���aI�䣢�" )rY�RrH�Y-V�X��'�)T�ٸy�6֬��Y,�N7JS�s� h
�ҬoN��/~�֘�P�Rq�8�)ie�ʤ[�]-0Ǯ��79#���H��-v�Zm�D՚k}UWkڻNu+�pwo�Qi=i��0zO�]�r���Q�h/(��jL4��F�‶�4��2�R1��Ϫ9��f�J(v$��>����,{%ͪ��L�����,��jP�B?�5@U �=�x���p�3��*c�a���M�l�!�b��s��z�����1z'�1cf*6�eܼ���9�~܀
�'՚��͢�r�/�g��m<�	��Dt��l�����l����J����Z�feS�A����&�	bV0|PF��[R�gh��V
��������jüi8cN1Z�R��\�~UPVtA}�����TX9�g��jsRs�f��gYgo+]vũRi��)w��c�x��bB�q�I�rժ���K����DϤ����9�e��9 ��}�*a��Vɡ���=j�Q�ռ��P���yS�P���k�w�Q��xJ:W�̱G�&��d��A;>����DI�2}�+߮%;��%�e]^�4ep.�v���R��,��ҺӲF$`��y��S�L1��R�)�<h���rj��`��'߳�ǌ�{�wЏ|d�؈Bz� TE��_q��d`��1JQ�0�P)�R}=�j1<�TU�������)�d�&������z]
zXB�U�Yn5ֶ��]qJǜ��F�p�P�|a,�sE���3��������J&�-��>�X���E}�]Ѭ����x�}=_��^Kthh�r�ؼ��*B`�l����Hc��|#������b����f�*L1���K$3�y��΢w��z0��rZ�41��E�����:��x]/FT�)�SxBe`W@��R݉�n�L�Zo����M�S�9̓g��,9��C\�a��~�K~��c'��NƧ0�dG�S�iѸ^�ո��X�'����7�N��ng5G�����=��ۓ	%52��?��h���nb�Nw�],nXZ[Z5�9��˼ٟ�\z��	!�&���h.+'���J.�U�������i)x���L��O�����fV���g�z�}�M�2g��3Q6ʚ[�9��B����1�%)��Ux�jb�6�,`/9����,o(����?���4�"&�F�O�2���u5t��`�#��Z�!�B7��Y�K��R�.ܪE{*�4{�J��E�PQW~k��"~�q�x=�OT���3\\�*p�D��ғ,�b�+QXO�������u�gLeٰ���aC6��E6v�6��a�϶��ހ��G��`��Aw���X8|ߝ1���lᎈ������[by@o��������0�T��-9M�-�9�NM�?���:�C�e����f�iN��!~7���%�Ft׉���DGm��9���^::��`>�!��֨K..h ﴋ�v$�\q�N��)E��sR������ݪ[�%�=b\ }��KR621P�Fx�C=�=�H6�L��كǒFnv�l�����H��\�*���)�z��jdsqteub����}�4��X��a��2W���杉Q�>�Ɯ�{���ބ{1�Iq��c59�6�,(q����u��69�氅ë*��C>j�� ���k�¦0y�[�~�I�a��qj���R�|@6��L����J��duC؛� ����a-J��Q
t7,1��B����Gca]¬�Bh�2�L�~�O-�b��]{�H49���q�j��^Oeְ7qr��ZY�a.�m7�x�AW@��0�( ��8�8�{�1�?T��j��0�O%�.�:)�M;�̕�*¼��kn5\��
K��r�T�p�S��l�+nT^1\���z0^1fb�6�VzZ��5�5���}����5�8��QB��9��F-A��n����(��'p��Xg8��N�i���rd����rp@u�Bs��b��Nf-e�O��4���y#�-Y՝RUI���qe���ٱ��9d�԰wo(k��Q���Pi�����m��p��QlÊH�&��d	�<��0$��T��Fy�r��`ZD�QY������{��<���P�ℙ�!81��}��}^�G8t��0U=}��߻��#�DRA܅}����;>�V��^dH�?J�=���sz�.?��@�'��ɒ�.q̄�MNeG����.1\���ʏY@��%%��Y4Β�+����-L9V$GH�H�+�N�`l��
�Q&�[�z��S'ܾՙ�b��'�8��=v��i�j��ǫ���u]��5L��K��"�1���E�nX��	�+7v'���6��*�0�F/Ҭ�`�Xu� ���<���3�s6hB����;E�����n��������f�tΡ�p	f��ft-h+z�Lw�1��I=���
�Q�h�j�z+���X{���s�l�J5|!;6\K�#\Iao���X���0��2.���Xa�<���:�+y���:c��H��у�,v^�f�
���@uUu^�>�4�T�N]�d���<�|L9�N�Tf����8=D+�03��q� �+E�Zy��
G\��J�҃M)H��+�C��dk$	��K
U�:�TG�Q0Tr�B�C��a����0�] ?��c_'�e�FtMjH\�E>�<�L8h�)
9�Z�q\d�'�82��E�ejH���T]r�#�h(b�'Edȣ�d��]]]q��\�2׮�?��?�.H^�=�B`�'�R5S��<-�*��.�M�f�9mR�ǃ���@1_ E[WL�U�Z/��5 (��W��u������r��G�^`�3f4�5�
�?^����lOO�f�#�9�
�9���%'q6*m�CP��
��.@I��-�x�m��n���-��U����]
��	��X:Z�F�WY�I$kԨ���ȕ.��ArX�y�3Ӻ������I���W�:������_<a¸劂�����himܨ��ɜq�{�*�5W��cL�AX!*
���]�`�|l2�����mǠ#q��U�59�LᵊJ�fj�K��t���'Mh����mF�U�Y
��]q]�f�ʠ������i�,�A���5̛�r���'��4;��)tZL1r�:��ىh� k	�3��X%��g�ф
s|�����2�)�4�J�����'�<��AsU	N4�ۮ�ѣ��xS�����RE�)w�q����8e��ā](�)��@S�m`�X�;ݗk>�1n)��3��	�`�0�1��}=���Fď�����=��Q�z�  6�C��"���V;��|-�1K�]t�b�?�!�]}�n�:��Ξ�4�H`�d�@���G�~Mn8��h��Vފ������kr�]�뜐˸�6����i�=��+�Pb��4��|c�P��� +���Ws0�[	;h)�D^!W�!&1�ñW=!���=���S���=	n�pB�+��*�r���[�a�<�ش�f��V�9A�J����}K<n
�
c��-�:+
�!�w>
'���W��W��d������
l��=��b1�Y�QkuzD��H;���0k!ꪺN1"�M���&�g-�A;�e��5\8�:��6Ny�񊇧8T:U��9k�;8��#�L�b�e����:XPu�rOD&��M��Z�5B<\m�=�*L$�[p|����ZV���WSn�T���K����M�웕�<��]!�]��+|�}����g�8.�: dѭ[�L��Q�Z@�9��Rc��
�$!�*����P^a[���6X�|���OVC���"��$�:ܴ��b�*�ܹ��-z"yJ��x���>�N��5)�)�1E6�0G�"��E��V<�焭.Ql���5��%0n�4"���8�7'С�5�BR������zA`9(r���);F{�u =�I�i~Y�6�L��`�d6"�Ma.��r�D��ݍa?�Ь��
�,��~�Pp:cIK��Ip�F�tY���v��$2k���HsE+d	' ��%����b��x��B҅�mDe�6���P�*�v7� ��ē��A�θᥨ̬�tx�B��f$�ʠ�7L�K��d��j���z,�Y�U�o �6���� п�DK�j��%N�5��)+7h����T��ŖZ�]����$rG˭bu/�پY���\�~�����uu������J�.:*�%��9+I%�;.@�P(�k�u�b��'�b�h��U�w���4���I8-�"���*���0Xx	
4B�	�lʩ�Y�~Y�����%>���z��z86nbʁ�H�T4�@O����R�l�+EF� ��Bٗ�g���\4��@�� �ZxQEG���^�����26�ֆ��4�^8��db��2��2`U,�fL,.a��
GN�/MUE���'[7T����,�̭V����9L�P��|�Bj����Ql�R�yY���`Z�+Vԣ����a!_�N)��\��&!���j*̴Z��X�sc�UoÒe�XkPd&��R)�
�=�W�R + �/�V��I3�Q�����צƪq��6���Q;TP
�d������:���	7k�?�_�]�A�tQ���?��xOa&���$�YwƐ��6����D���l�.��ʐ~TU�]�cݩ3,�m�,݊�x�	h�cw���M`�ծ�i��
�Abت^R�+���-}��5 ��2��6I=Ӧ�I$a
e�[֩j�~��Ym��.F!.jFO�	Sb����vU-��J���r�8j�K-��2�����O�$���F(�Rq���w�m
`=��YӀ�s�iO����5�&{�%��2��y^��ۍ<z��F�t�]@A��۹�+�+��oae��uu*3��@uKTB��[F`iS谇Kl�a�b⍮�e���$���p�G���V�@Z���cLj��z+R
A0��̞�K��wK���d%��7�M�f�ҥ؞1e[�z��+>,��0OJ'�1�Z��P�v4���
��s�Ê3��]�}g��z���{��i�_�up���t.,N-�\���Q@'N6O��WQ��|S/���b��% ��$'N�w-d�S���������(�i�sr��Ob]�'I@ɉ+�^���"L���\�4c��j��k��ܼ7w�%��_���Ew�ȹ����<��D���P ��Mp�
�֦�ڦ��(5*��:W�N3�G�w�1���W�

...[TRUNCATED by ctxpack to fit budget]...
```
