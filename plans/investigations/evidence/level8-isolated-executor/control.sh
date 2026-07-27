set -eu
printf 'uid=%s\n' "$(id -u)"
printf 'pids=%s\n' "$(cat /sys/fs/cgroup/pids.max)"
printf 'memory=%s\n' "$(cat /sys/fs/cgroup/memory.max)"
printf 'cpu=%s\n' "$(cat /sys/fs/cgroup/cpu.max)"
printf 'interfaces=%s\n' "$(ls /sys/class/net)"
test -z "${GH_TOKEN+x}"
test ! -e /operator-host-sentinel
grep -q '^overlay / overlay ro,' /proc/mounts
printf 'root_read_only=true\n'
sleep 1
printf 'isolation_controls_passed=true\n'
