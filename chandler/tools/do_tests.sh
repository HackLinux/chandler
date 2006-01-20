#!/bin/bash

#
# script to run all Chandler unit, functional and performance tests
#
# Scans the chandler/ tree for any sub-directory that is named 
# "tests" and then within that directory calls RunPython for any
# file named Test*.py
#
# if CHANDLER_PERFORMANCE_TEST=yes then CATS Performance Tests are run
# if CHANDLER_FUNCTIONAL_TEST=no then CATS Functional Tests are skipped
#

NO_ARGS=0 
E_OPTERROR=65

USAGE="Usage: `basename $0` -fpu [-t test_name] chandler-base-path"

if [ ! -n "$1" ]; then
    echo $USAGE
    echo if CHANDLER_FUNCTIONAL_TEST=yes or -f then CATS Functional Tests are run
    echo if CHANDLER_PERFORMANCE_TEST=yes or -p then CATS Performance Tests are run
    echo if CHANDLER_UNIT_TEST=yes or -u then Chandler Unit Tests are run
    echo "if a specific test name or (pattern) is given using -t then only that test name will be run"
    exit $E_OPTERROR
fi

if [ "$CHANDLER_FUNCTIONAL_TEST" = "yes" ]; then
    RUN_FUNCTIONAL=yes
else
    RUN_FUNCTIONAL=no
fi
if [ "$CHANDLER_PERFORMANCE_TEST" = "yes" ]; then
    RUN_PERFORMANCE=yes
else
    RUN_PERFORMANCE=no
fi
if [ "$CHANDLER_UNIT_TEST" = "yes" ]; then
    RUN_UNIT=yes
else
    RUN_UNIT=no
fi

while getopts ":fput:" Option
do
  case $Option in
    f ) RUN_FUNCTIONAL=yes;;
    p ) RUN_PERFORMANCE=yes;;
    u ) RUN_UNIT=yes;;
    t ) TEST_TO_RUN=$OPTARG;;
    * ) echo "Unimplemented option chosen.";;   # DEFAULT
  esac
done

  # leave any remaining command line parameters on the command line
shift $(($OPTIND - 1))

C_DIR="$1"
T_DIR=$C_DIR

if [ ! -d "$C_DIR/i18n" ]; then
    C_DIR=`pwd`

    if [ ! -d "$C_DIR/i18n" ]; then
        echo Error: The path [$C_DIR] given does not point to a chandler/ directory
        echo $USAGE
        exit 65
    else
        echo Using current directory [$C_DIR] as the chandler/ directory
    fi
fi

if [ "$CHANDLERBIN" = "" ]
then
    CHANDLERBIN="$C_DIR"
fi

HH_DIR=`pwd`
TESTLOG="$C_DIR/do_tests.log"
FAILED_TESTS=""

echo - + - + - + - + - + - + - + - + - + - + - + - + - + - + - + | tee -a $TESTLOG
echo Started `date`                                              | tee -a $TESTLOG
echo Setting up script environment                               | tee -a $TESTLOG

PP_DIR="$C_DIR/tools/QATestScripts/DataFiles"

if [ "$OSTYPE" = "cygwin" ]; then
    RUN_CHANDLER=RunChandler.bat
    RUN_PYTHON=RunPython.bat
    PP_DIR=`cygpath -w $PP_DIR`
else
    RUN_CHANDLER=RunChandler
    RUN_PYTHON=RunPython
fi

  # if the debug/ path is not found, then avoid debug tests
if [ ! -d $C_DIR/debug ]; then
    MODES="release"
    echo Skipping debug tests as $C_DIR/debug does not exist | tee -a $TESTLOG
else
    MODES="release debug"
fi

  # each directory to exclude should be place in the EXCLUDES array
  # and a 0 value should be place in the L_EXCLUDES array
  # the EXCLUDES array is then walked and the length of the 
  # directory is calculated - beats doing it by hand and making a mistake

EXCLUDES=("$C_DIR/release" "$C_DIR/debug" "$C_DIR/tools" "$C_DIR/util")
L_EXCLUDES=(0 0 0 0)
for item in 0 1 2 3 ; do
    L_EXCLUDES[$item]=${#EXCLUDES[$item]}
done

  # if a specific test name has been given then
  # find that test and run it

if [ -n "$TEST_TO_RUN" ]; then
    DIRS=`find $C_DIR -name $TEST_TO_RUN -print`

    if [ "$DIRS" = "" ]; then
        DIRS=`find $C_DIR -name $TEST_TO_RUN.py -print`
    fi

    if [ "$DIRS" = "" ]; then
        echo "Error: The test(s) you requested were not found:" ["$TEST_TO_RUN"]
        FAILED_TESTS="$TEST_TO_RUN"
    else
        for mode in $MODES ; do
            echo Running $mode | tee -a $TESTLOG

            for test in $DIRS ; do
                if [ "$OSTYPE" = "cygwin" ]; then
                    TESTNAME=`cygpath -w $test`
                else
                    TESTNAME=$test
                fi

                echo Running $TESTNAME | tee -a $TESTLOG

                cd $C_DIR

                if echo "$TESTNAME" | grep -q "QATestScripts/" ; then
                    $CHANDLERBIN/release/$RUN_CHANDLER --create --profileDir="$P_DIR" --scriptFile="$TESTNAME" &> $C_DIR/test.log
                    SUCCESS="#TINDERBOX# Status = PASSED"
                else
                    $CHANDLERBIN/$mode/$RUN_PYTHON $TESTNAME &> $C_DIR/test.log
                    SUCCESS="^OK"
                fi

                echo - - - - - - - - - - - - - - - - - - - - - - - - - - | tee -a $TESTLOG
                cat $C_DIR/test.log | tee -a $TESTLOG

                RESULT=`grep "$SUCCESS" $C_DIR/test.log`
                if [ "$RESULT" = "" ]; then
                    FAILED_TESTS="$FAILED_TESTS ($mode)$TESTNAME"
                fi
            done
        done
    fi
else
    if [ "$RUN_UNIT" = "yes" ]; then
        DIRS=`find $C_DIR -type d -name tests -print`

          # this code walks thru all the dirs with "tests" in their name
          # and then compares them to the exclude dir array by
          # taking the substring of the L_EXCLUDE length value
          # if there is a match, the loop is broken and the dir is skipped

        for item in $DIRS ; do
            FILEPATH=${item%/*}
            EXCLUDED=no
            for index in 0 1 2 3 ; do
                exclude=${EXCLUDES[$index]}
                len=${L_EXCLUDES[$index]}

                if [ "${FILEPATH:0:$len}" = "$exclude" ]; then
                    EXCLUDED=yes
                    break;
                fi
            done         
            if [ "$EXCLUDED" = "no" ]; then
                TESTDIRS="$TESTDIRS $item"
            fi
        done

          # walk thru all of the test dirs and find the test files

        for mode in $MODES ; do
            echo Running $mode unit tests | tee -a $TESTLOG

            for testdir in $TESTDIRS ; do
                TESTS=`find $testdir -name 'Test*.py' -print`

                for test in $TESTS ; do
                    if [ "$OSTYPE" = "cygwin" ]; then
                        TESTNAME=`cygpath -w $test`
                    else
                        TESTNAME=$test
                    fi

                    echo Running $TESTNAME | tee -a $TESTLOG

                    cd $C_DIR
                    $CHANDLERBIN/$mode/$RUN_PYTHON $TESTNAME &> $C_DIR/test.log

                      # scan the test output for the success messge "OK"
                    RESULT=`grep '^OK' $C_DIR/test.log`

                    echo - - - - - - - - - - - - - - - - - - - - - - - - - - | tee -a $TESTLOG
                    echo $TESTNAME [$RESULT] | tee -a $TESTLOG
                    cat $C_DIR/test.log      | tee -a $TESTLOG

                    if [ "$RESULT" = "" ]; then
                        FAILED_TESTS="$FAILED_TESTS ($mode)$TESTNAME"
                    fi
                done
            done
        done
    fi

      # if Functional Tests are needed - find the FunctionalTestSuite and run it

    if [ "$RUN_FUNCTIONAL" = "yes" ]; then
        echo Running $mode functional tests | tee -a $TESTLOG

        for mode in $MODES ; do
            test="$C_DIR/tools/QATestScripts/Functional/FunctionalTestSuite.py"

            if [ "$OSTYPE" = "cygwin" ]; then
                TESTNAME=`cygpath -w $test`
                P_DIR=`cygpath -w $C_DIR`
            else
                TESTNAME=$test
                P_DIR=$C_DIR
            fi
            if [ "$mode" = "debug" ]; then
                STDERR_FLAG="--stderr"
            else
                STDERR_FLAG=""
            fi

            echo Running $TESTNAME | tee -a $TESTLOG

            cd $C_DIR
            $CHANDLERBIN/$mode/$RUN_CHANDLER --create $STDERR_FLAG --profileDir="$P_DIR" --parcelPath="$PP_DIR" --scriptFile="$TESTNAME" &> $C_DIR/test.log

              # scan the test output for the success messge "OK"
            RESULT=`grep '#TINDERBOX# Status = PASSED' $C_DIR/test.log`

            echo - - - - - - - - - - - - - - - - - - - - - - - - - - | tee -a $TESTLOG
            echo $TESTNAME [$RESULT] | tee -a $TESTLOG
            cat $C_DIR/test.log      | tee -a $TESTLOG

            if [ "$RESULT" = "" ]; then
                FAILED_TESTS="$FAILED_TESTS ($mode)$TESTNAME"
            fi
        done
    fi

      # if Performance Tests are needed - walk the CATS directory
      # and create a list of all valid tests

    if [ "$RUN_PERFORMANCE" = "yes" ]; then
        echo Running performance tests | tee -a $TESTLOG

        TESTS=`find $C_DIR/tools/QATestScripts/Performance -name 'Perf*.py' -print`
        TIME_LOG=$C_DIR/time.log
        PERF_LOG=$C_DIR/perf.log
        if [ "$OSTYPE" = "cygwin" ]; then
            TIME_LOG=`cygpath -w $TIME_LOG`
            PERF_LOG=`cygpath -w $PERF_LOG`
        fi
        rm -f $PERF_LOG
        
        # First run tests with empty repository
        for test in $TESTS ; do
			rm -f $TIME_LOG
			            
            # Don't run large data tests here
            if [ `echo $test | grep -v PerfLargeData` ]; then
                
                if [ "$OSTYPE" = "cygwin" ]; then
                    TESTNAME=`cygpath -w $test`
                    P_DIR=`cygpath -w $C_DIR`
                else
                    TESTNAME=$test
                    P_DIR=$C_DIR
                fi
    
                echo -n $TESTNAME
                cd $C_DIR
                $CHANDLERBIN/release/$RUN_CHANDLER --create --profileDir="$P_DIR" --catsPerfLog="$TIME_LOG" --scriptFile="$TESTNAME" &> $C_DIR/test.log
    
                # scan the test output for the success message "OK"
                RESULT=`grep '#TINDERBOX# Status = PASSED' $C_DIR/test.log`
                
                if [ "$RESULT" = "" ]; then
                    RESULT=Failed
                else
                    RESULT=`cat $TIME_LOG`s
                fi
                
                echo \ [ $RESULT ] | tee -a $TESTLOG
                echo - + - + - + - + - + - + - + - + - + - + - + - + - + - + - + >> $PERF_LOG
                cat $C_DIR/test.log >> $PERF_LOG
    
                if [ "$RESULT" = "Failed" ]; then
                    FAILED_TESTS="$FAILED_TESTS $TESTNAME"
                fi
            fi
        done
        
        echo -n Creating a large repository backup for the remaining tests
        rm -fr $C_DIR/__repository__.0*
        REPO=$C_DIR/__repository__.001
        BACKUP_REPO=$C_DIR/tools/QATestScripts/Performance/LargeDataBackupRepository.py
        if [ "$OSTYPE" = "cygwin" ]; then
            REPO=`cygpath -w $REPO`
            BACKUP_REPO=`cygpath -w $BACKUP_REPO`
        fi
        
        cd $C_DIR
        $CHANDLERBIN/release/$RUN_CHANDLER --create --profileDir="$P_DIR" --catsPerfLog="$TIME_LOG" --scriptFile="$BACKUP_REPO" &> $PERF_LOG
        
        # scan the test output for the success message "OK"
        RESULT=`grep '#TINDERBOX# Status = PASSED' $C_DIR/test.log`
        
        if [ "$RESULT" = "" ]; then
            for test in $TESTS ; do
                FAILED_TESTS="$FAILED_TESTS $test"
            done
        else
            # Show the time it took to create backup
        	echo \ \[`<$TIME_LOG`s\]
        	
            # Then run large data tests with restored large repository
            for test in $TESTS ; do
                rm -f $TIME_LOG
                
                # Run only large data tests
                if [ `echo $test | grep PerfLargeData` ]; then
                
                    if [ "$OSTYPE" = "cygwin" ]; then
                        TESTNAME=`cygpath -w $test`
                        P_DIR=`cygpath -w $C_DIR`
                    else
                        TESTNAME=$test
                        P_DIR=$C_DIR
                    fi
        
                    echo -n $TESTNAME
                    cd $C_DIR
                    $CHANDLERBIN/release/$RUN_CHANDLER --restore="$REPO" --profileDir="$P_DIR" --catsPerfLog="$TIME_LOG" --scriptFile="$TESTNAME" &> $C_DIR/test.log
        
                    # scan the test output for the success message "OK"
                    RESULT=`grep '#TINDERBOX# Status = PASSED' $C_DIR/test.log`
                    
                    if [ "$RESULT" = "" ]; then
                        RESULT=Failed
                    else
                        RESULT=`cat $TIME_LOG`s
                    fi
                    
                    echo \ [ $RESULT ] | tee -a $TESTLOG
                    echo - + - + - + - + - + - + - + - + - + - + - + - + - + - + - + >> $PERF_LOG
                    cat $C_DIR/test.log >> $PERF_LOG

                    if [ "$RESULT" = "Failed" ]; then
                        FAILED_TESTS="$FAILED_TESTS $TESTNAME"
                    fi
                fi
            done
        fi

        SLEEP_TIME=5
        echo Showing performance log in $SLEEP_TIME seconds, Ctrl+C to stop tests
        sleep $SLEEP_TIME
        cat $PERF_LOG
    fi
fi

echo - + - + - + - + - + - + - + - + - + - + - + - + - + - + - + | tee -a $TESTLOG

if [ "$FAILED_TESTS" = "" ]; then
    echo All tests passed | tee -a $TESTLOG
else
    echo The following tests failed | tee -a $TESTLOG

    for item in $FAILED_TESTS ; do
        echo "    $item" | tee -a $TESTLOG
    done
fi
