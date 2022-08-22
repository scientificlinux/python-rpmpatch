setup_file(){
    [ -d ./venv  ] ||  ./create_and_fix_venv.sh
    . ./venv/bin/activate
    rpmdev-wipetree || rpmdev-setuptree
}

@test "Empty should print examples and exit 1" {
    run ./rpmpatch/patchsrpm.py
    [ "$status" -eq 1 ]
    echo $output | fgrep -q -- "-h, --help"
    echo $output | fgrep -q -- "--sampleconfig"
    echo $output | fgrep -q "Examples:"
}

@test "Sample config" {
    run ./rpmpatch/patchsrpm.py --sampleconfig
    [ "$status" -eq 1 ]
    echo $output | fgrep -q -- "[patch2]"
    echo $output | fgrep -q -- "[re1]"
}

@test "Build the authd without --keep_dist" {
    rpmdev-wipetree
    run ./rpmpatch/patchsrpm.py --config=$BATS_TEST_DIRNAME/test-resources/test-config/ $BATS_TEST_DIRNAME/test-resources/srpms/authd-1.4.4-5.el8_0.1.src.rpm
    [ "$status" -eq 0 ]
    compgen -G "$HOME/rpmbuild/SRPMS/authd*1.src.rpm"
}

@test "Build the authd with --keep_dist and then test src.rpm" {
    SRPM="$HOME/rpmbuild/SRPMS/authd-1.4.4-5.el8_0.1.src.rpm"
    OUTPUT_DIR="authd-1.4.4-5.el8_0.1.src"
    
    [ -d $OUTPUT_DIR ] && rm -r ${OUTPUT_DIR} || true
    rpmdev-wipetree
    run ./rpmpatch/patchsrpm.py --keep_dist --config=$BATS_TEST_DIRNAME/test-resources/test-config/ $BATS_TEST_DIRNAME/test-resources/srpms/authd-1.4.4-5.el8_0.1.src.rpm
    [ "$status" -eq 0 ]
    rpmdev-extract $SRPM
    # tests for re1
    grep -q 420421 $OUTPUT_DIR/authd.spec
    grep -q change-rfc-1413-to-420421 $OUTPUT_DIR/authd.spec

    # tests for source1
    grep 'Source3:.*test_file' $OUTPUT_DIR/authd.spec
    grep 'test' $OUTPUT_DIR/test_file
    [ -e $OUTPUT_DIR/test_file ]
    # tests for removing patch1
    [ "$(grep -c "Patch[[:digit:]]\+.*authd-covscan.patch" $OUTPUT_DIR/authd.spec)" -eq 0 ] 
    grep 'Removed Patch: authd-covscan.patch' -q $OUTPUT_DIR/authd.spec
    [ -d $OUTPUT_DIR ] && rm -r ${OUTPUT_DIR}
}

@test "Build modular_rpm with --keep_dist - check dist and add changelog-user" {
    SRPM_NAME=389-ds-base-1.4.3.16-16.module+el8.4.0+11446+fc96bc48.src.rpm
    rpmdev-wipetree
    run ./rpmpatch/patchsrpm.py --changelog_user='test user <test@example.com>' --keep_dist --config=$BATS_TEST_DIRNAME/test-resources/test-config/ $BATS_TEST_DIRNAME/test-resources/srpms/$SRPM_NAME
    SRPM="$HOME/rpmbuild/SRPMS/$SRPM_NAME"
    [ -e "$HOME/rpmbuild/SRPMS/$SRPM_NAME" ]

}
