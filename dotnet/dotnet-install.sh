#!/usr/bin/env bash
# Copyright (c) .NET Foundation and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.
#

# Stop script on NZEC
set -e
# Stop script if unbound variable found (use ${var:-} if intentional)
set -u
# By default cmd1 | cmd2 returns exit code of cmd2 regardless of cmd1 success
# This is causing it to fail
set -o pipefail

# Use in the the functions: eval $invocation
invocation='say_verbose "Calling: ${yellow:-}${FUNCNAME[0]} ${green:-}$*${normal:-}"'

# standard output may be used as a return value in the functions
# we need a way to write text on the screen in the functions so that
# it won't interfere with the return value.
# Exposing stream 3 as a pipe to standard output of the script itself
exec 3>&1

# Setup some colors to use. These need to work in fairly limited shells, like the Ubuntu Docker container where there are only 8 colors.
# See if stdout is a terminal
if [ -t 1 ] && command -v tput > /dev/null; then
    # see if it supports colors
    ncolors=$(tput colors || echo 0)
    if [ -n "$ncolors" ] && [ $ncolors -ge 8 ]; then
        bold="$(tput bold       || echo)"
        normal="$(tput sgr0     || echo)"
        black="$(tput setaf 0   || echo)"
        red="$(tput setaf 1     || echo)"
        green="$(tput setaf 2   || echo)"
        yellow="$(tput setaf 3  || echo)"
        blue="$(tput setaf 4    || echo)"
        magenta="$(tput setaf 5 || echo)"
        cyan="$(tput setaf 6    || echo)"
        white="$(tput setaf 7   || echo)"
    fi
fi

say_warning() {
    printf "%b\n" "${yellow:-}dotnet_install: Warning: $1${normal:-}" >&3
}

say_err() {
    printf "%b\n" "${red:-}dotnet_install: Error: $1${normal:-}" >&2
}

say() {
    # using stream 3 (defined in the beginning) to not interfere with stdout of functions
    # which may be used as return value
    printf "%b\n" "${cyan:-}dotnet-install:${normal:-} $1" >&3
}

say_verbose() {
    if [ "$verbose" = true ]; then
        say "$1"
    fi
}

# This platform list is finite - if the SDK/Runtime has supported Linux distribution-specific assets,
#   then and only then should the Linux distribution appear in this list.
# Adding a Linux distribution to this list does not imply distribution-specific support.
get_legacy_os_name_from_platform() {
    eval $invocation

    platform="$1"
    case "$platform" in
        "centos.7")
            echo "centos"
            return 0
            ;;
        "debian.8")
            echo "debian"
            return 0
            ;;
        "debian.9")
            echo "debian.9"
            return 0
            ;;
        "fedora.23")
            echo "fedora.23"
            return 0
            ;;
        "fedora.24")
            echo "fedora.24"
            return 0
            ;;
        "fedora.27")
            echo "fedora.27"
            return 0
            ;;
        "fedora.28")
            echo "fedora.28"
            return 0
            ;;
        "opensuse.13.2")
            echo "opensuse.13.2"
            return 0
            ;;
        "opensuse.42.1")
            echo "opensuse.42.1"
            return 0
            ;;
        "opensuse.42.3")
            echo "opensuse.42.3"
            return 0
            ;;
        "rhel.7"*)
            echo "rhel"
            return 0
            ;;
        "ubuntu.14.04")
            echo "ubuntu"
            return 0
            ;;
        "ubuntu.16.04")
            echo "ubuntu.16.04"
            return 0
            ;;
        "ubuntu.16.10")
            echo "ubuntu.16.10"
            return 0
            ;;
        "ubuntu.18.04")
            echo "ubuntu.18.04"
            return 0
            ;;
        "alpine.3.4.3")
            echo "alpine"
            return 0
            ;;
    esac
    return 1
}

get_legacy_os_name() {
    eval $invocation

    local uname=$(uname)
    if [ "$uname" = "Darwin" ]; then
        echo "osx"
        return 0
    elif [ -n "$runtime_id" ]; then
        echo $(get_legacy_os_name_from_platform "${runtime_id%-*}" || echo "${runtime_id%-*}")
        return 0
    else
        if [ -e /etc/os-release ]; then
            . /etc/os-release
            os=$(get_legacy_os_name_from_platform "$ID${VERSION_ID:+.${VERSION_ID}}" || echo "")
            if [ -n "$os" ]; then
                echo "$os"
                return 0
            fi
        fi
    fi

    say_verbose "Distribution specific OS name and version could not be detected: UName = $uname"
    return 1
}

get_linux_platform_name() {
    eval $invocation

    if [ -n "$runtime_id" ]; then
        echo "${runtime_id%-*}"
        return 0
    else
        if [ -e /etc/os-release ]; then
            . /etc/os-release
            echo "$ID${VERSION_ID:+.${VERSION_ID}}"
            return 0
        elif [ -e /etc/redhat-release ]; then
            local redhatRelease=$(</etc/redhat-release)
            if [[ $redhatRelease == "CentOS release 6."* || $redhatRelease == "Red Hat Enterprise Linux "*" release 6."* ]]; then
                echo "rhel.6"
                return 0
            fi
        fi
    fi

    say_verbose "Linux specific platform name and version could not be detected: UName = $uname"
    return 1
}

is_musl_based_distro() {
    (ldd --version 2>&1 || true) | grep -q musl
}

get_current_os_name() {
    eval $invocation

    local uname=$(uname)
    if [ "$uname" = "Darwin" ]; then
        echo "osx"
        return 0
    elif [ "$uname" = "FreeBSD" ]; then
        echo "freebsd"
        return 0
    elif [ "$uname" = "Linux" ]; then
        local linux_platform_name=""
        linux_platform_name="$(get_linux_platform_name)" || true

        if [ "$linux_platform_name" = "rhel.6" ]; then
            echo $linux_platform_name
            return 0
        elif is_musl_based_distro; then
            echo "linux-musl"
            return 0
        elif [ "$linux_platform_name" = "linux-musl" ]; then
            echo "linux-musl"
            return 0
        else
            echo "linux"
            return 0
        fi
    fi

    say_err "OS name could not be detected: UName = $uname"
    return 1
}

machine_has() {
    eval $invocation

    command -v "$1" > /dev/null 2>&1
    return $?
}

check_min_reqs() {
    local hasMinimum=false
    if machine_has "curl"; then
        hasMinimum=true
    elif machine_has "wget"; then
        hasMinimum=true
    fi

    if [ "$hasMinimum" = "false" ]; then
        say_err "curl (recommended) or wget are required to download dotnet. Install missing prerequisite to proceed."
        return 1
    fi
    return 0
}

# args:
# input - $1
to_lowercase() {
    #eval $invocation

    echo "$1" | tr '[:upper:]' '[:lower:]'
    return 0
}

# args:
# input - $1
remove_trailing_slash() {
    #eval $invocation

    local input="${1:-}"
    echo "${input%/}"
    return 0
}

# args:
# input - $1
remove_beginning_slash() {
    #eval $invocation

    local input="${1:-}"
    echo "${input#/}"
    return 0
}

# args:
# root_path - $1
# child_path - $2 - this parameter can be empty
combine_paths() {
    eval $invocation

    # TODO: Consider making it work with any number of paths. For now:
    if [ ! -z "${3:-}" ]; then
        say_err "combine_paths: Function takes two parameters."
        return 1
    fi

    local root_path="$(remove_trailing_slash "$1")"
    local child_path="$(remove_beginning_slash "${2:-}")"
    say_verbose "combine_paths: root_path=$root_path"
    say_verbose "combine_paths: child_path=$child_path"
    echo "$root_path/$child_path"
    return 0
}

get_machine_architecture() {
    eval $invocation

    if command -v uname > /dev/null; then
        CPUName=$(uname -m)
        case $CPUName in
        armv1*|armv2*|armv3*|armv4*|armv5*|armv6*)
            echo "armv6-or-below"
            return 0
            ;;
        armv*l)
            echo "arm"
            return 0
            ;;
        aarch64|arm64)
            if [ "$(getconf LONG_BIT)" -lt 64 ]; then
                # This is 32-bit OS running on 64-bit CPU (for example Raspberry Pi OS)
                echo "arm"
                return 0
            fi
            echo "arm64"
            return 0
            ;;
        s390x)
            echo "s390x"
            return 0
            ;;
        ppc64le)
            echo "ppc64le"
            return 0
            ;;
        loongarch64)
            echo "loongarch64"
            return 0
            ;;
        riscv64)
            echo "riscv64"
            return 0
            ;;
        powerpc|ppc)
            echo "ppc"
            return 0
            ;;
        esac
    fi

    # Always default to 'x64'
    echo "x64"
    return 0
}

# args:
# architecture - $1
get_normalized_architecture_from_architecture() {
    eval $invocation

    local architecture="$(to_lowercase "$1")"

    if [[ $architecture == \<auto\> ]]; then
        machine_architecture="$(get_machine_architecture)"
        if [[ "$machine_architecture" == "armv6-or-below" ]]; then
            say_err "Architecture \`$machine_architecture\` not supported. If you think this is a bug, report it at https://github.com/dotnet/install-scripts/issues"
            return 1
        fi

        echo $machine_architecture
        return 0
    fi

    case "$architecture" in
        amd64|x64)
            echo "x64"
            return 0
            ;;
        arm)
            echo "arm"
            return 0
            ;;
        arm64)
            echo "arm64"
            return 0
            ;;
        s390x)
            echo "s390x"
            return 0
            ;;
        ppc64le)
            echo "ppc64le"
            return 0
            ;;
        loongarch64)
            echo "loongarch64"
            return 0
            ;;
    esac

    say_err "Architecture \`$architecture\` not supported. If you think this is a bug, report it at https://github.com/dotnet/install-scripts/issues"
    return 1
}

# args:
# version - $1
# channel - $2
# architecture - $3
get_normalized_architecture_for_specific_sdk_version() {
    eval $invocation

    local is_version_support_arm64="$(is_arm64_supported "$1")"
    local is_channel_support_arm64="$(is_arm64_supported "$2")"
    local architecture="$3";
    local osname="$(get_current_os_name)"

    if [ "$osname" == "osx" ] && [ "$architecture" == "arm64" ] && { [ "$is_version_support_arm64" = false ] || [ "$is_channel_support_arm64" = false ]; }; then
        #check if rosetta is installed
        if [ "$(/usr/bin/pgrep oahd >/dev/null 2>&1;echo $?)" -eq 0 ]; then 
            say_verbose "Changing user architecture from '$architecture' to 'x64' because .NET SDKs prior to version 6.0 do not support arm64." 
            echo "x64"
            return 0;
        else
            say_err "Architecture \`$architecture\` is not supported for .NET SDK version \`$version\`. Please install Rosetta to allow emulation of the \`$architecture\` .NET SDK on this platform"
            return 1
        fi
    fi

    echo "$architecture"
    return 0
}

# args:
# version or channel - $1
is_arm64_supported() {
    # Extract the major version by splitting on the dot
    major_version="${1%%.*}"

    # Check if the major version is a valid number and less than 6
    case "$major_version" in
        [0-9]*)  
            if [ "$major_version" -lt 6 ]; then
                echo false
                return 0
            fi
            ;;
    esac

    echo true
    return 0
}

# args:
# user_defined_os - $1
get_normalized_os() {
    eval $invocation

    local osname="$(to_lowercase "$1")"
    if [ ! -z "$osname" ]; then
        case "$osname" in
            osx | freebsd | rhel.6 | linux-musl | linux)
                echo "$osname"
                return 0
                ;;
            macos)
                osname='osx'
                echo "$osname"
                return 0
                ;;
            *)
                say_err "'$user_defined_os' is not a supported value for --os option, supported values are: osx, macos, linux, linux-musl, freebsd, rhel.6. If you think this is a bug, report it at https://github.com/dotnet/install-scripts/issues."
                return 1
                ;;
        esac
    else
        osname="$(get_current_os_name)" || return 1
    fi
    echo "$osname"
    return 0
}

# args:
# quality - $1
get_normalized_quality() {
    eval $invocation

    local quality="$(to_lowercase "$1")"
    if [ ! -z "$quality" ]; then
        case "$quality" in
            daily | preview)
                echo "$quality"
                return 0
                ;;
            ga)
                #ga quality is available without specifying quality, so normalizing it to empty
                return 0
                ;;
            *)
                say_err "'$quality' is not a supported value for --quality option. Supported values are: daily, preview, ga. If you think this is a bug, report it at https://github.com/dotnet/install-scripts/issues."
                return 1
                ;;
        esac
    fi
    return 0
}

# args:
# channel - $1
get_normalized_channel() {
    eval $invocation

    local channel="$(to_lowercase "$1")"

    if [[ $channel == current ]]; then
        say_warning 'Value "Current" is deprecated for -Channel option. Use "STS" instead.'
    fi

    if [[ $channel == release/* ]]; then
        say_warning 'Using branch name with -Channel option is no longer supported with newer releases. Use -Quality option with a channel in X.Y format instead.';
    fi

    if [ ! -z "$channel" ]; then
        case "$channel" in
            lts)
                echo "LTS"
                return 0
                ;;
            sts)
                echo "STS"
                return 0
                ;;
            current)
                echo "STS"
                return 0
                ;;
            *)
                echo "$channel"
                return 0
                ;;
        esac
    fi

    return 0
}

# args:
# runtime - $1
get_normalized_product() {
    eval $invocation

    local product=""
    local runtime="$(to_lowercase "$1")"
    if [[ "$runtime" == "dotnet" ]]; then
        product="dotnet-runtime"
    elif [[ "$runtime" == "aspnetcore" ]]; then
        product="aspnetcore-runtime"
    elif [ -z "$runtime" ]; then
        product="dotnet-sdk"
    fi
    echo "$product"
    return 0
}

# The version text returned from the feeds is a 1-line or 2-line string:
# For the SDK and the dotnet runtime (2 lines):
# Line 1: # commit_hash
# Line 2: # 4-part version
# For the aspnetcore runtime (1 line):
# Line 1: # 4-part version

# args:
# version_text - stdin
get_version_from_latestversion_file_content() {
    eval $invocation

    cat | tail -n 1 | sed 's/\r$//'
    return 0
}

# args:
# install_root - $1
# relative_path_to_package - $2
# specific_version - $3
is_dotnet_package_installed() {
    eval $invocation

    local install_root="$1"
    local relative_path_to_package="$2"
    local specific_version="${3//[$'\t\r\n']}"

    local dotnet_package_path="$(combine_paths "$(combine_paths "$install_root" "$relative_path_to_package")" "$specific_version")"
    say_verbose "is_dotnet_package_installed: dotnet_package_path=$dotnet_package_path"

    if [ -d "$dotnet_package_path" ]; then
        return 0
    else
        return 1
    fi
}

# args:
# downloaded file - $1
# remote_file_size - $2
validate_remote_local_file_sizes() 
{
    eval $invocation

    local downloaded_file="$1"
    local remote_file_size="$2"
    local file_size=''

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        file_size="$(stat -c '%s' "$downloaded_file")"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # hardcode in order to avoid conflicts with GNU stat
        file_size="$(/usr/bin/stat -f '%z' "$downloaded_file")"
    fi  
    
    if [ -n "$file_size" ]; then
        say "Downloaded file size is $file_size bytes."

        if [ -n "$remote_file_size" ] && [ -n "$file_size" ]; then
            if [ "$remote_file_size" -ne "$file_size" ]; then
                say "The remote and local file sizes are not equal. The remote file size is $remote_file_size bytes and the local size is $file_size bytes. The local package may be corrupted."
            else
                say "The remote and local file sizes are equal."
            fi
        fi
        
    else
        say "Either downloaded or local package size can not be measured. One of them may be corrupted."      
    fi 
}

# args:
# azure_feed - $1
# channel - $2
# normalized_architecture - $3
get_version_from_latestversion_file() {
    eval $invocation

    local azure_feed="$1"
    local channel="$2"
    local normalized_architecture="$3"

    local version_file_url=null
    if [[ "$runtime" == "dotnet" ]]; then
        version_file_url="$azure_feed/Runtime/$channel/latest.version"
    elif [[ "$runtime" == "aspnetcore" ]]; then
        version_file_url="$azure_feed/aspnetcore/Runtime/$channel/latest.version"
    elif [ -z "$runtime" ]; then
         version_file_url="$azure_feed/Sdk/$channel/latest.version"
    else
        say_err "Invalid value for \$runtime"
        return 1
    fi
    say_verbose "get_version_from_latestversion_file: latest url: $version_file_url"

    download "$version_file_url" || return $?
    return 0
}

# args:
# json_file - $1
parse_globaljson_file_for_version() {
    eval $invocation

    local json_file="$1"
    if [ ! -f "$json_file" ]; then
        say_err "Unable to find \`$json_file\`"
        return 1
    fi

    sdk_section=$(cat $json_file | tr -d "\r" | awk '/"sdk"/,/}/')
    if [ -z "$sdk_section" ]; then
        say_err "Unable to parse the SDK node in \`$json_file\`"
        return 1
    fi

    sdk_list=$(echo $sdk_section | awk -F"[{}]" '{print $2}')
    sdk_list=${sdk_list//[\" ]/}
    sdk_list=${sdk_list//,/$'\n'}

    local version_info=""
    while read -r line; do
      IFS=:
      while read -r key value; do
        if [[ "$key" == "version" ]]; then
          version_info=$value
        fi
      done <<< "$line"
    done <<< "$sdk_list"
    if [ -z "$version_info" ]; then
        say_err "Unable to find the SDK:version node in \`$json_file\`"
        return 1
    fi

    unset IFS;
    echo "$version_info"
    return 0
}

# args:
# azure_feed - $1
# channel - $2
# normalized_architecture - $3
# version - $4
# json_file - $5
get_specific_version_from_version() {
    eval $invocation

    local azure_feed="$1"
    local channel="$2"
    local normalized_architecture="$3"
    local version="$(to_lowercase "$4")"
    local json_file="$5"

    if [ -z "$json_file" ]; then
        if [[ "$version" == "latest" ]]; then
            local version_info
            version_info="$(get_version_from_latestversion_file "$azure_feed" "$channel" "$normalized_architecture" false)" || return 1
            say_verbose "get_specific_version_from_version: version_info=$version_info"
            echo "$version_info" | get_version_from_latestversion_file_content
            return 0
        else
            echo "$version"
            return 0
        fi
    else
        local version_info
        version_info="$(parse_globaljson_file_for_version "$json_file")" || return 1
        echo "$version_info"
        return 0
    fi
}

# args:
# azure_feed - $1
# channel - $2
# normalized_architecture - $3
# specific_version - $4
# normalized_os - $5
construct_download_link() {
    eval $invocation

    local azure_feed="$1"
    local channel="$2"
    local normalized_architecture="$3"
    local specific_version="${4//[$'\t\r\n']}"
    local specific_product_version="$(get_specific_product_version "$1" "$4")"
    local osname="$5"

    local download_link=null
    if [[ "$runtime" == "dotnet" ]]; then
        download_link="$azure_feed/Runtime/$specific_version/dotnet-runtime-$specific_product_version-$osname-$normalized_architecture.tar.gz"
    elif [[ "$runtime" == "aspnetcore" ]]; then
        download_link="$azure_feed/aspnetcore/Runtime/$specific_version/aspnetcore-runtime-$specific_product_version-$osname-$normalized_architecture.tar.gz"
    elif [ -z "$runtime" ]; then
        download_link="$azure_feed/Sdk/$specific_version/dotnet-sdk-$specific_product_version-$osname-$normalized_architecture.tar.gz"
    else
        return 1
    fi

    echo "$download_link"
    return 0
}

# args:
# azure_feed - $1
# specific_version - $2
# download link - $3 (optional)
get_specific_product_version() {
    # If we find a 'productVersion.txt' at the root of any folder, we'll use its contents
    # to resolve the version of what's in the folder, superseding the specified version.
    # if 'productVersion.txt' is missing but download link is already available, product version will be taken from download link
    eval $invocation

    local azure_feed="$1"
    local specific_version="${2//[$'\t\r\n']}"
    local package_download_link=""
    if [ $# -gt 2  ]; then
        local package_download_link="$3"
    fi
    local specific_product_version=null

    # Try to get the version number, using the productVersion.txt file located next to the installer file.
    local download_links=($(get_specific_product_version_url "$azure_feed" "$specific_version" true "$package_download_link")
        $(get_specific_product_version_url "$azure_feed" "$specific_version" false "$package_download_link"))

    for download_link in "${download_links[@]}"
    do
        say_verbose "Checking for the existence of $download_link"

        if machine_has "curl"
        then
            if ! specific_product_version=$(curl -s --fail "${download_link}${feed_credential}" 2>&1); then
                continue
            else
                echo "${specific_product_version//[$'\t\r\n']}"
                return 0
            fi

        elif machine_has "wget"
        then
            specific_product_version=$(wget -qO- "${download_link}${feed_credential}" 2>&1)
            if [ $? = 0 ]; then
                echo "${specific_product_version//[$'\t\r\n']}"
                return 0
            fi
        fi
    done
    
    # Getting the version number with productVersion.txt has failed. Try parsing the download link for a version number.
    say_verbose "Failed to get the version using productVersion.txt file. Download link will be parsed instead."
    specific_product_version="$(get_product_specific_version_from_download_link "$package_download_link" "$specific_version")"
    echo "${specific_product_version//[$'\t\r\n']}"
    return 0
}

# args:
# azure_feed - $1
# specific_version - $2
# is_flattened - $3
# download link - $4 (optional)
get_specific_product_version_url() {
    eval $invocation

    local azure_feed="$1"
    local specific_version="$2"
    local is_flattened="$3"
    local package_download_link=""
    if [ $# -gt 3  ]; then
        local package_download_link="$4"
    fi

    local pvFileName="productVersion.txt"
    if [ "$is_flattened" = true ]; then
        if [ -z "$runtime" ]; then
            pvFileName="sdk-productVersion.txt"
        elif [[ "$runtime" == "dotnet" ]]; then
            pvFileName="runtime-productVersion.txt"
        else
            pvFileName="$runtime-productVersion.txt"
        fi
    fi

    local download_link=null

    if [ -z "$package_download_link" ]; then
        if [[ "$runtime" == "dotnet" ]]; then
            download_link="$azure_feed/Runtime/$specific_version/${pvFileName}"
        elif [[ "$runtime" == "aspnetcore" ]]; then
            download_link="$azure_feed/aspnetcore/Runtime/$specific_version/${pvFileName}"
        elif [ -z "$runtime" ]; then
            download_link="$azure_feed/Sdk/$specific_version/${pvFileName}"
        else
            return 1
        fi
    else
        download_link="${package_download_link%/*}/${pvFileName}"
    fi

    say_verbose "Constructed productVersion link: $download_link"
    echo "$download_link"
    return 0
}

# args:
# download link - $1
# specific version - $2
get_product_specific_version_from_download_link()
{
    eval $invocation

    local download_link="$1"
    local specific_version="$2"
    local specific_product_version="" 

    if [ -z "$download_link" ]; then
        echo "$specific_version"
        return 0
    fi

    #get filename
    filename="${download_link##*/}"

    #product specific version follows the product name
    #for filename 'dotnet-sdk-3.1.404-linux-x64.tar.gz': the product version is 3.1.404
    IFS='-'
    read -ra filename_elems <<< "$filename"
    count=${#filename_elems[@]}
    if [[ "$count" -gt 2 ]]; then
        specific_product_version="${filename_elems[2]}"
    else
        specific_product_version=$specific_version
    fi
    unset IFS;
    echo "$specific_product_version"
    return 0
}

# args:
# azure_feed - $1
# channel - $2
# normalized_architecture - $3
# specific_version - $4
construct_legacy_download_link() {
    eval $invocation

    local azure_feed="$1"
    local channel="$2"
    local normalized_architecture="$3"
    local specific_version="${4//[$'\t\r\n']}"

    local distro_specific_osname
    distro_specific_osname="$(get_legacy_os_name)" || return 1

    local legacy_download_link=null
    if [[ "$runtime" == "dotnet" ]]; then
        legacy_download_link="$azure_feed/Runtime/$specific_version/dotnet-$distro_specific_osname-$normalized_architecture.$specific_version.tar.gz"
    elif [ -z "$runtime" ]; then
        legacy_download_link="$azure_feed/Sdk/$specific_version/dotnet-dev-$distro_specific_osname-$normalized_architecture.$specific_version.tar.gz"
    else
        return 1
    fi

    echo "$legacy_download_link"
    return 0
}

get_user_install_path() {
    eval $invocation

    if [ ! -z "${DOTNET_INSTALL_DIR:-}" ]; then
        echo "$DOTNET_INSTALL_DIR"
    else
        echo "$HOME/.dotnet"
    fi
    return 0
}

# args:
# install_dir - $1
resolve_installation_path() {
    eval $invocation

    local install_dir=$1
    if [ "$install_dir" = "<auto>" ]; then
        local user_install_path="$(get_user_install_path)"
        say_verbose "resolve_installation_path: user_install_path=$user_install_path"
        echo "$user_install_path"
        return 0
    fi

    echo "$install_dir"
    return 0
}

# args:
# relative_or_absolute_path - $1
get_absolute_path() {
    eval $invocation

    local relative_or_absolute_path=$1
    echo "$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1")"
    return 0
}

# args:
# override - $1 (boolean, true or false)
get_cp_options() {
    eval $invocation

    local override="$1"
    local override_switch=""

    if [ "$override" = false ]; then
        override_switch="-n"

        # create temporary files to check if 'cp -u' is supported
        tmp_dir="$(mktemp -d)"
        tmp_file="$tmp_dir/testfile"
        tmp_file2="$tmp_dir/testfile2"

        touch "$tmp_file"

        # use -u instead of -n if it's available
        if cp -u "$tmp_file" "$tmp_file2" 2>/dev/null; then
            override_switch="-u"
        fi

        # clean up
        rm -f "$tmp_file" "$tmp_file2"
        rm -rf "$tmp_dir"
    fi

    echo "$override_switch"
}

# args:
# input_files - stdin
# root_path - $1
# out_path - $2
# override - $3
copy_files_or_dirs_from_list() {
    eval $invocation

    local root_path="$(remove_trailing_slash "$1")"
    local out_path="$(remove_trailing_slash "$2")"
    local override="$3"
    local override_switch="$(get_cp_options "$override")"

    cat | uniq | while read -r file_path; do
        local path="$(remove_beginning_slash "${file_path#$root_path}")"
        local target="$out_path/$path"
        if [ "$override" = true ] || (! ([ -d "$target" ] || [ -e "$target" ])); then
            mkdir -p "$out_path/$(dirname "$path")"
            if [ -d "$target" ]; then
                rm -rf "$target"
            fi
            cp -R $override_switch "$root_path/$path" "$target"
        fi
    done
}

# args:
# zip_uri - $1
get_remote_file_size() {
    local zip_uri="$1"

    if machine_has "curl"; then
        file_size=$(curl -sI  "$zip_uri" | grep -i content-length | awk '{ num = $2 + 0; print num }')
    elif machine_has "wget"; then
        file_size=$(wget --spider --server-response -O /dev/null "$zip_uri" 2>&1 | grep -i 'Content-Length:' | awk '{ num = $2 + 0; print num }')
    else
        say "Neither curl nor wget is available on this system."
        return
    fi

    if [ -n "$file_size" ]; then
        say "Remote file $zip_uri size is $file_size bytes."
        echo "$file_size"
    else
        say_verbose "Content-Length header was not extracted for $zip_uri."
        echo ""
    fi
}

# args:
# zip_path - $1
# out_path - $2
# remote_file_size - $3
extract_dotnet_package() {
    eval $invocation

    local zip_path="$1"
    local out_path="$2"
    local remote_file_size="$3"

    local temp_out_path="$(mktemp -d "$temporary_file_template")"

    local failed=false
    tar -xzf "$zip_path" -C "$temp_out_path" > /dev/null || failed=true

    local folders_with_version_regex='^.*/[0-9]+\.[0-9]+[^/]+/'
    find "$temp_out_path" -type f | grep -Eo "$folders_with_version_regex" | sort | copy_files_or_dirs_from_list "$temp_out_path" "$out_path" false
    find "$temp_out_path" -type f | grep -Ev "$folders_with_version_regex" | copy_files_or_dirs_from_list "$temp_out_path" "$out_path" "$override_non_versioned_files"
    
    validate_remote_local_file_sizes "$zip_path" "$remote_file_size"
    
    rm -rf "$temp_out_path"
    if [ -z ${keep_zip+x} ]; then
        rm -f "$zip_path" && say_verbose "Temporary archive file $zip_path was removed"
    fi

    if [ "$failed" = true ]; then
        say_err "Extraction failed"
        return 1
    fi
    return 0
}

# args:
# remote_path - $1
# disable_feed_credential - $2
get_http_header()
{
    eval $invocation
    local remote_path="$1"
    local disable_feed_credential="$2"

    local failed=false
    local response
    if machine_has "curl"; then
        get_http_header_curl $remote_path $disable_feed_credential || failed=true
    elif machine_has "wget"; then
        get_http_header_wget $remote_path $disable_feed_credential || failed=true
    else
        failed=true
    fi
    if [ "$failed" = true ]; then
        say_verbose "Failed to get HTTP header: '$remote_path'."
        return 1
    fi
    return 0
}

# args:
# remote_path - $1
# disable_feed_credential - $2
get_http_header_curl() {
    eval $invocation
    local remote_path="$1"
    local disable_feed_credential="$2"

    remote_path_with_credential="$remote_path"
    if [ "$disable_feed_credential" = false ]; then
        remote_path_with_credential+="$feed_credential"
    fi

    curl_options="-I -sSL --retry 5 --retry-delay 2 --connect-timeout 15 "
    curl $curl_options "$remote_path_with_credential" 2>&1 || return 1
    return 0
}

# args:
# remote_path - $1
# disable_feed_credential - $2
get_http_header_wget() {
    eval $invocation
    local remote_path="$1"
    local disable_feed_credential="$2"
    local wget_options="-q -S --spider --tries 5 "

    local wget_options_extra=''

    # Test for options that aren't supported on all wget implementations.
    if [[ $(wget -h 2>&1 | grep -E 'waitretry|connect-timeout') ]]; then
        wget_options_extra="--waitretry 2 --connect-timeout 15 "
    else
        say "wget extra options are unavailable for this environment"
    fi

    remote_path_with_credential="$remote_path"
    if [ "$disable_feed_credential" = false ]; then
        remote_path_with_credential+="$feed_credential"
    fi

    wget $wget_options $wget_options_extra "$remote_path_with_credential" 2>&1

    return $?
}

# args:
# remote_path - $1
# [out_path] - $2 - stdout if not provided
download() {
    eval $invocation

    local remote_path="$1"
    local out_path="${2:-}"

    if [[ "$remote_path" != "http"* ]]; then
        cp "$remote_path" "$out_path"
        return $?
    fi

    local failed=false
    local attempts=0
    while [ $attempts -lt 3 ]; do
        attempts=$((attempts+1))
        failed=false
        if machine_has "curl"; then
            downloadcurl "$remote_path" "$out_path" || failed=true
        elif machine_has "wget"; then
            downloadwget "$remote_path" "$out_path" || failed=true
        else
            say_err "Missing dependency: neither curl nor wget was found."
            exit 1
        fi

        if [ "$failed" = false ] || [ $attempts -ge 3 ] || { [ ! -z $http_code ] && [ $http_code = "404" ]; }; then
            break
        fi

        say "Download attempt #$attempts has failed: $http_code $download_error_msg"
        say "Attempt #$((attempts+1)) will start in $((attempts*10)) seconds."
        sleep $((attempts*10))
    done

    if [ "$failed" = true ]; then
        say_verbose "Download failed: $remote_path"
        return 1
    fi
    return 0
}

# Updates global variables $http_code and $download_error_msg
downloadcurl() {
    eval $invocation
    unset http_code
    unset download_error_msg
    local remote_path="$1"
    local out_path="${2:-}"
    # Append feed_credential as late as possible before calling curl to avoid logging feed_credential
    # Avoid passing URI with credentials to functions: note, most of them echoing parameters of invocation in verbose output.
    local remote_path_with_credential="${remote_path}${feed_credential}"
    local curl_options="--retry 20 --retry-delay 2 --connect-timeout 15 -sSL -f --create-dirs "
    local curl_exit_code=0;
    if [ -z "$out_path" ]; then
        curl_output=$(curl $curl_options "$remote_path_with_credential" 2>&1)
        curl_exit_code=$?
        echo "$curl_output"
    else
        curl_output=$(curl $curl_options -o "$out_path" "$remote_path_with_credential" 2>&1)
        curl_exit_code=$?
    fi

    # Regression in curl causes curl with --retry to return a 0 exit code even when it fails to download a file - https://github.com/curl/curl/issues/17554
    if [ $curl_exit_code -eq 0 ] && echo "$curl_output" | grep -q "^curl: ([0-9]*) "; then
        curl_exit_code=$(echo "$curl_output" | sed 's/curl: (\([0-9]*\)).*/\1/')
    fi

    if [ $curl_exit_code -gt 0 ]; then
        download_error_msg="Unable to download $remote_path."
        # Check for curl timeout codes
        if [[ $curl_exit_code == 7 || $curl_exit_code == 28 ]]; then
            download_error_msg+=" Failed to reach the server: connection timeout."
        else
            local disable_feed_credential=false
            local response=$(get_http_header_curl $remote_path $disable_feed_credential)
            http_code=$( echo "$response" | awk '/^HTTP/{print $2}' | tail -1 )
            if  [[ ! -z $http_code && $http_code != 2* ]]; then
                download_error_msg+=" Returned HTTP status code: $http_code."
            fi
        fi
        say_verbose "$download_error_msg"
        return 1
    fi
    return 0
}


# Updates global variables $http_code and $download_error_msg
downloadwget() {
    eval $invocation
    unset http_code
    unset download_error_msg
    local remote_path="$1"
    local out_path="${2:-}"
    # Append feed_credential as late as possible before calling wget to avoid logging feed_credential
    local remote_path_with_credential="${remote_path}${feed_credential}"
    local wget_options="--tries 20 "

    local wget_options_extra=''
    local wget_result=''

    # Test for options that aren't supported on all wget implementations.
    if [[ $(wget -h 2>&1 | grep -E 'waitretry|connect-timeout') ]]; then
        wget_options_extra="--waitretry 2 --connect-timeout 15 "
    else
        say "wget extra options are unavailable for this environment"
    fi

    if [ -z "$out_path" ]; then
        wget -q $wget_options $wget_options_extra -O - "$remote_path_with_credential" 2>&1
        wget_result=$?
    else
        wget $wget_options $wget_options_extra -O "$out_path" "$remote_path_with_credential" 2>&1
        wget_result=$?
    fi

    if [[ $wget_result != 0 ]]; then
        local disable_feed_credential=false
        local response=$(get_http_header_wget $remote_path $disable_feed_credential)
        http_code=$( echo "$response" | awk '/^  HTTP/{print $2}' | tail -1 )
        download_error_msg="Unable to download $remote_path."
        if  [[ ! -z $http_code && $http_code != 2* ]]; then
            download_error_msg+=" Returned HTTP status code: $http_code."
        # wget exit code 4 stands for network-issue
        elif [[ $wget_result == 4 ]]; then
            download_error_msg+=" Failed to reach the server: connection timeout."
        fi
        say_verbose "$download_error_msg"
        return 1
    fi

    return 0
}

get_download_link_from_aka_ms() {
    eval $invocation

    #quality is not supported for LTS or STS channel
    #STS maps to current
    if [[ ! -z "$normalized_quality"  && ("$normalized_channel" == "LTS" || "$normalized_channel" == "STS") ]]; then
        normalized_quality=""
        say_warning "Specifying quality for STS or LTS channel is not supported, the quality will be ignored."
    fi

    say_verbose "Retrieving primary payload URL from aka.ms for channel: '$normalized_channel', quality: '$normalized_quality', product: '$normalized_product', os: '$normalized_os', architecture: '$normalized_architecture'." 

    #construct aka.ms link
    aka_ms_link="https://aka.ms/dotnet"
    if  [ "$internal" = true ]; then
        aka_ms_link="$aka_ms_link/internal"
    fi
    aka_ms_link="$aka_ms_link/$normalized_channel"
    if [[ ! -z "$normalized_quality" ]]; then
        aka_ms_link="$aka_ms_link/$normalized_quality"
    fi
    aka_ms_link="$aka_ms_link/$normalized_product-$normalized_os-$normalized_architecture.tar.gz"
    say_verbose "Constructed aka.ms link: '$aka_ms_link'."

    #get HTTP response
    #do not pass credentials as a part of the $aka_ms_link and do not apply credentials in the get_http_header function
    #otherwise the redirect link would have credentials as well
    #it would result in applying credentials twice to the resulting link and thus breaking it, and in echoing credentials to the output as a part of redirect link
    disable_feed_credential=true
    response="$(get_http_header $aka_ms_link $disable_feed_credential)"

    say_verbose "Received response: $response"
    # Get results of all the redirects.
    http_codes=$( echo "$response" | awk '$1 ~ /^HTTP/ {print $2}' )
    # They all need to be 301, otherwise some links are broken (except for the last, which is not a redirect but 200 or 404).
    broken_redirects=$( echo "$http_codes" | sed '$d' | grep -v '301' )
    # The response may end without final code 2xx/4xx/5xx somehow, e.g. network restrictions on www.bing.com causes redirecting to bing.com fails with connection refused.
    # In this case it should not exclude the last.
    last_http_code=$(  echo "$http_codes" | tail -n 1 )
    if ! [[ $last_http_code =~ ^(2|4|5)[0-9][0-9]$ ]]; then
        broken_redirects=$( echo "$http_codes" | grep -v '301' )
    fi

    # All HTTP codes are 301 (Moved Permanently), the redirect link exists.
    if [[ -z "$broken_redirects" ]]; then
        aka_ms_download_link=$( echo "$response" | awk '$1 ~ /^Location/{print $2}' | tail -1 | tr -d '\r')

        if [[ -z "$aka_ms_download_link" ]]; then
            say_verbose "The aka.ms link '$aka_ms_link' is not valid: failed to get redirect location."
            return 1
        fi

        say_verbose "The redirect location retrieved: '$aka_ms_download_link'."
        return 0
    else
        say_verbose "The aka.ms link '$aka_ms_link' is not valid: received HTTP code: $(echo "$broken_redirects" | paste -sd "," -)."
        return 1
    fi
}

get_feeds_to_use()
{
    feeds=(
    "https://builds.dotnet.microsoft.com/dotnet"
    "https://ci.dot.net/public"
    )

    if [[ -n "$azure_feed" ]]; then
        feeds=("$azure_feed")
    fi

    if [[ -n "$uncached_feed" ]]; then
        feeds=("$uncached_feed")
    fi
}

# THIS FUNCTION MAY EXIT (if the determined version is already installed).
generate_download_links() {

    download_links=()
    specific_versions=()
    effective_versions=()
    link_types=()

    # If generate_akams_links returns false, no fallback to old links. Just terminate.
    # This function may also 'exit' (if the determined version is already installed).
    generate_akams_links || return

    # Check other feeds only if we haven't been able to find an aka.ms link.
    if [[ "${#download_links[@]}" -lt 1 ]]; then
        for feed in ${feeds[@]}
        do
            # generate_regular_links may also 'exit' (if the determined version is already installed).
            generate_regular_links $feed || return
        done
    fi

    if [[ "${#download_links[@]}" -eq 0 ]]; then
        say_err "Failed to resolve the exact version number."
        return 1
    fi

    say_verbose "Generated ${#download_links[@]} links."
    for link_index in ${!download_links[@]}
    do
        say_verbose "Link $link_index: ${link_types[$link_index]}, ${effective_versions[$link_index]}, ${download_links[$link_index]}"
    done
}

# THIS FUNCTION MAY EXIT (if the determined version is already installed).
generate_akams_links() {
    local valid_aka_ms_link=true;

    normalized_version="$(to_lowercase "$version")"
    if [[ "$normalized_version" != "latest" ]] && [ -n "$normalized_quality" ]; then
        say_err "Quality and Version options are not allowed to be specified simultaneously. See https://learn.microsoft.com/dotnet/core/tools/dotnet-install-script#options for details."
        return 1
    fi

    if [[ -n "$json_file" || "$normalized_version" != "latest" ]]; then
        # aka.ms links are not needed when exact version is specified via command or json file
        return
    fi

    get_download_link_from_aka_ms || valid_aka_ms_link=false

    if [[ "$valid_aka_ms_link" == true ]]; then
        say_verbose "Retrieved primary payload URL from aka.ms link: '$aka_ms_download_link'."
        say_verbose "Downloading using legacy url will not be attempted."

        download_link=$aka_ms_download_link

        #get version from the path
        IFS='/'
        read -ra pathElems <<< "$download_link"
        count=${#pathElems[@]}
        specific_version="${pathElems[count-2]}"
        unset IFS;
        say_verbose "Version: '$specific_version'."

        #Retrieve effective version
        effective_version="$(get_specific_product_version "$azure_feed" "$specific_version" "$download_link")"

        # Add link info to arrays
        download_links+=($download_link)
        specific_versions+=($specific_version)
        effective_versions+=($effective_version)
        link_types+=("aka.ms")

        #  Check if the SDK version is already installed.
        if [[ "$dry_run" != true ]] && is_dotnet_package_installed "$install_root" "$asset_relative_path" "$effective_version"; then
            say "$asset_name with version '$effective_version' is already installed."
            exit 0
        fi

        return 0
    fi

    # if quality is specified - exit with error - there is no fallback approach
    if [ ! -z "$normalized_quality" ]; then
        say_err "Failed to locate the latest version in the channel '$normalized_channel' with '$normalized_quality' quality for '$normalized_product', os: '$normalized_os', architecture: '$normalized_architecture'."
        say_err "Refer to: https://aka.ms/dotnet-os-lifecycle for information on .NET Core support."
        return 1
    fi
    say_verbose "Falling back to latest.version file approach."
}

# THIS FUNCTION MAY EXIT (if the determined version is already installed)
# args:
# feed - $1
generate_regular_links() {
    local feed="$1"
    local valid_legacy_download_link=true

    specific_version=$(get_specific_version_from_version "$feed" "$channel" "$normalized_architecture" "$version" "$json_file") || specific_version='0'

    if [[ "$specific_version" == '0' ]]; then
        say_verbose "Failed to resolve the specific version number using feed '$feed'"
        return
    fi

    effective_version="$(get_specific_product_version "$feed" "$specific_version")"
    say_verbose "specific_version=$specific_version"

    download_link="$(construct_download_link "$feed" "$channel" "$normalized_architecture" "$specific_version" "$normalized_os")"
    say_verbose "Constructed primary named payload URL: $download_link"

    # Add link info to arrays
    download_links+=($download_link)
    specific_versions+=($specific_version)
    effective_versions+=($effective_version)
    link_types+=("primary")

    legacy_download_link="$(construct_legacy_download_link "$feed" "$channel" "$normalized_architecture" "$specific_version")" || valid_legacy_download_link=false

    if [ "$valid_legacy_download_link" = true ]; then
        say_verbose "Constructed legacy named payload URL: $legacy_download_link"
    
        download_links+=($legacy_download_link)
        specific_versions+=($specific_version)
        effective_versions+=($effective_version)
        link_types+=("legacy")
    else
        legacy_download_link=""
        say_verbose "Could not construct a legacy_download_link; omitting..."
    fi

    #  Check if the SDK version is already installed.
    if [[ "$dry_run" != true ]] && is_dotnet_package_installed "$install_root" "$asset_relative_path" "$effective_version"; then
        say "$asset_name with version '$effective_version' is already installed."
        exit 0
    fi
}

print_dry_run() {

    say "Payload URLs:"

    for link_index in "${!download_links[@]}"
        do
            say "URL #$link_index - ${link_types[$link_index]}: ${download_links[$link_index]}"
    done

    resolved_version=${specific_versions[0]}
    repeatable_command="./$script_name --version "\""$resolved_version"\"" --install-dir "\""$install_root"\"" --architecture "\""$normalized_architecture"\"" --os "\""$normalized_os"\"""
    
    if [ ! -z "$normalized_quality" ]; then
        repeatable_command+=" --quality "\""$normalized_quality"\"""
    fi

    if [[ "$runtime" == "dotnet" ]]; then
        repeatable_command+=" --runtime "\""dotnet"\"""
    elif [[ "$runtime" == "aspnetcore" ]]; then
        repeatable_command+=" --runtime "\""aspnetcore"\"""
    fi

    repeatable_command+="$non_dynamic_parameters"

    if [ -n "$feed_credential" ]; then
        repeatable_command+=" --feed-credential "\""<feed_credential>"\"""
    fi

    say "Repeatable invocation: $repeatable_command"
}

calculate_vars() {
    eval $invocation

    script_name=$(basename "$0")
    normalized_architecture="$(get_normalized_architecture_from_architecture "$architecture")"
    say_verbose "Normalized architecture: '$normalized_architecture'."
    normalized_os="$(get_normalized_os "$user_defined_os")"
    say_verbose "Normalized OS: '$normalized_os'."
    normalized_quality="$(get_normalized_quality "$quality")"
    say_verbose "Normalized quality: '$normalized_quality'."
    normalized_channel="$(get_normalized_channel "$channel")"
    say_verbose "Normalized channel: '$normalized_channel'."
    normalized_product="$(get_normalized_product "$runtime")"
    say_verbose "Normalized product: '$normalized_product'."
    install_root="$(resolve_installation_path "$install_dir")"
    say_verbose "InstallRoot: '$install_root'."

    normalized_architecture="$(get_normalized_architecture_for_specific_sdk_version "$version" "$normalized_channel" "$normalized_architecture")"

    if [[ "$runtime" == "dotnet" ]]; then
        asset_relative_path="shared/Microsoft.NETCore.App"
        asset_name=".NET Core Runtime"
    elif [[ "$runtime" == "aspnetcore" ]]; then
        asset_relative_path="shared/Microsoft.AspNetCore.App"
        asset_name="ASP.NET Core Runtime"
    elif [ -z "$runtime" ]; then
        asset_relative_path="sdk"
        asset_name=".NET Core SDK"
    fi

    get_feeds_to_use
}

install_dotnet() {
    eval $invocation
    local download_failed=false
    local download_completed=false
    local remote_file_size=0

    mkdir -p "$install_root"
    zip_path="${zip_path:-$(mktemp "$temporary_file_template")}"
    say_verbose "Archive path: $zip_path"

    for link_index in "${!download_links[@]}"
    do
        download_link="${download_links[$link_index]}"
        specific_version="${specific_versions[$link_index]}"
        effective_version="${effective_versions[$link_index]}"
        link_type="${link_types[$link_index]}"

        say "Attempting to download using $link_type link $download_link"

        # The download function will set variables $http_code and $download_error_msg in case of failure.
        download_failed=false
        download "$download_link" "$zip_path" 2>&1 || download_failed=true

        if [ "$download_failed" = true ]; then
            case $http_code in
            404)
                say "The resource at $link_type link '$download_link' is not available."
                ;;
            *)
                say "Failed to download $link_type link '$download_link': $http_code $download_error_msg"
                ;;
            esac
            rm -f "$zip_path" 2>&1 && say_verbose "Temporary archive file $zip_path was removed"
        else
            download_completed=true
            break
        fi
    done

    if [[ "$download_completed" == false ]]; then
        say_err "Could not find \`$asset_name\` with version = $specific_version"
        say_err "Refer to: https://aka.ms/dotnet-os-lifecycle for information on .NET Core support"
        return 1
    fi

    remote_file_size="$(get_remote_file_size "$download_link")"

    say "Extracting archive from $download_link"
    extract_dotnet_package "$zip_path" "$install_root" "$remote_file_size" || return 1

    #  Check if the SDK version is installed; if not, fail the installation.
    # if the version contains "RTM" or "servicing"; check if a 'release-type' SDK version is installed.
    if [[ $specific_version == *"rtm"* || $specific_version == *"servicing"* ]]; then
        IFS='-'
        read -ra verArr <<< "$specific_version"
        release_version="${verArr[0]}"
        unset IFS;
        say_verbose "Checking installation: version = $release_version"
        if is_dotnet_package_installed "$install_root" "$asset_relative_path" "$release_version"; then
            say "Installed version is $effective_version"
            return 0
        fi
    fi

    #  Check if the standard SDK version is installed.
    say_verbose "Checking installation: version = $effective_version"
    if is_dotnet_package_installed "$install_root" "$asset_relative_path" "$effective_version"; then
        say "Installed version is $effective_version"
        return 0
    fi

    # Version verification failed. More likely something is wrong either with the downloaded content or with the verification algorithm.
    say_err "Failed to verify the version of installed \`$asset_name\`.\nInstallation source: $download_link.\nInstallation location: $install_root.\nReport the bug at https://github.com/dotnet/install-scripts/issues."
    say_err "\`$asset_name\` with version = $effective_version failed to install with an error."
    return 1
}

args=("$@")

local_version_file_relative_path="/.version"
bin_folder_relative_path=""
temporary_file_template="${TMPDIR:-/tmp}/dotnet.XXXXXXXXX"

channel="LTS"
version="Latest"
json_file=""
install_dir="<auto>"
architecture="<auto>"
dry_run=false
no_path=false
azure_feed=""
uncached_feed=""
feed_credential=""
verbose=false
runtime=""
runtime_id=""
quality=""
internal=false
override_non_versioned_files=true
non_dynamic_parameters=""
user_defined_os=""

while [ $# -ne 0 ]
do
    name="$1"
    case "$name" in
        -c|--channel|-[Cc]hannel)
            shift
            channel="$1"
            ;;
        -v|--version|-[Vv]ersion)
            shift
            version="$1"
            ;;
        -q|--quality|-[Qq]uality)
            shift
            quality="$1"
            ;;
        --internal|-[Ii]nternal)
            internal=true
            non_dynamic_parameters+=" $name"
            ;;
        -i|--install-dir|-[Ii]nstall[Dd]ir)
            shift
            install_dir="$1"
            ;;
        --arch|--architecture|-[Aa]rch|-[Aa]rchitecture)
            shift
            architecture="$1"
            ;;
        --os|-[Oo][SS])
            shift
            user_defined_os="$1"
            ;;
        --shared-runtime|-[Ss]hared[Rr]untime)
            say_warning "The --shared-runtime flag is obsolete and may be removed in a future version of this script. The recommended usage is to specify '--runtime dotnet'."
            if [ -z "$runtime" ]; then
                runtime="dotnet"
            fi
            ;;
        --runtime|-[Rr]untime)
            shift
            runtime="$1"
            if [[ "$runtime" != "dotnet" ]] && [[ "$runtime" != "aspnetcore" ]]; then
                say_err "Unsupported value for --runtime: '$1'. Valid values are 'dotnet' and 'aspnetcore'."
                if [[ "$runtime" == "windowsdesktop" ]]; then
                    say_err "WindowsDesktop archives are manufactured for Windows platforms only."
                fi
                exit 1
            fi
            ;;
        --dry-run|-[Dd]ry[Rr]un)
            dry_run=true
            ;;
        --no-path|-[Nn]o[Pp]ath)
            no_path=true
            non_dynamic_parameters+=" $name"
            ;;
        --verbose|-[Vv]erbose)
            verbose=true
            non_dynamic_parameters+=" $name"
            ;;
        --azure-feed|-[Aa]zure[Ff]eed)
            shift
            azure_feed="$1"
            non_dynamic_parameters+=" $name "\""$1"\"""
            ;;
        --uncached-feed|-[Uu]ncached[Ff]eed)
            shift
            uncached_feed="$1"
            non_dynamic_parameters+=" $name "\""$1"\"""
            ;;
        --feed-credential|-[Ff]eed[Cc]redential)
            shift
            feed_credential="$1"
            #feed_credential should start with "?", for it to be added to the end of the link.
            #adding "?" at the beginning of the feed_credential if needed.
            [[ -z "$(echo $feed_credential)" ]] || [[ $feed_credential == \?* ]] || feed_credential="?$feed_credential"
            ;;
        --runtime-id|-[Rr]untime[Ii]d)
            shift
            runtime_id="$1"
            non_dynamic_parameters+=" $name "\""$1"\"""
            say_warning "Use of --runtime-id is obsolete and should be limited to the versions below 2.1. To override architecture, use --architecture option instead. To override OS, use --os option instead."
            ;;
        --jsonfile|-[Jj][Ss]on[Ff]ile)
            shift
            json_file="$1"
            ;;
        --skip-non-versioned-files|-[Ss]kip[Nn]on[Vv]ersioned[Ff]iles)
            override_non_versioned_files=false
            non_dynamic_parameters+=" $name"
            ;;
        --keep-zip|-[Kk]eep[Zz]ip)
            keep_zip=true
            non_dynamic_parameters+=" $name"
            ;;
        --zip-path|-[Zz]ip[Pp]ath)
            shift
            zip_path="$1"
            ;;
        -?|--?|-h|--help|-[Hh]elp)
            script_name="dotnet-install.sh"
            echo ".NET Tools Installer"
            echo "Usage:"
            echo "       # Install a .NET SDK of a given Quality from a given Channel"
            echo "       $script_name [-c|--channel <CHANNEL>] [-q|--quality <QUALITY>]"
            echo "       # Install a .NET SDK of a specific public version"
            echo "       $script_name [-v|--version <VERSION>]"
            echo "       $script_name -h|-?|--help"
            echo ""
            echo "$script_name is a simple command line interface for obtaining dotnet cli."
            echo "    Note that the intended use of this script is for Continuous Integration (CI) scenarios, where:"
            echo "    - The SDK needs to be installed without user interaction and without admin rights."
            echo "    - The SDK installation doesn't need to persist across multiple CI runs."
            echo "    To set up a development environment or to run apps, use installers rather than this script. Visit https://dotnet.microsoft.com/download to get the installer."
            echo ""
            echo "Options:"
            echo "  -c,--channel <CHANNEL>         Download from the channel specified, Defaults to \`$channel\`."
            echo "      -Channel"
            echo "          Possible values:"
            echo "          - STS - the most recent Standard Term Support release"
            echo "          - LTS - the most recent Long Term Support release"
            echo "          - 2-part version in a format A.B - represents a specific release"
            echo "              examples: 2.0; 1.0"
            echo "          - 3-part version in a format A.B.Cxx - represents a specific SDK release"
            echo "              examples: 5.0.1xx, 5.0.2xx."
            echo "              Supported since 5.0 release"
            echo "          Warning: Value 'Current' is deprecated for the Channel parameter. Use 'STS' instead."
            echo "          Note: The version parameter overrides the channel parameter when any version other than 'latest' is used."
            echo "  -v,--version <VERSION>         Use specific VERSION, Defaults to \`$version\`."
            echo "      -Version"
            echo "          Possible values:"
            echo "          - latest - the latest build on specific channel"
            echo "          - 3-part version in a format A.B.C - represents specific version of build"
            echo "              examples: 2.0.0-preview2-006120; 1.1.0"
            echo "  -q,--quality <quality>         Download the latest build of specified quality in the channel."
            echo "      -Quality"
            echo "          The possible values are: daily, preview, GA."
            echo "          Works only in combination with channel. Not applicable for STS and LTS channels and will be ignored if those channels are used." 
            echo "          For SDK use channel in A.B.Cxx format. Using quality for SDK together with channel in A.B format is not supported." 
            echo "          Supported since 5.0 release." 
            echo "          Note: The version parameter overrides the channel parameter when any version other than 'latest' is used, and therefore overrides the quality."
            echo "  --internal,-Internal               Download internal builds. Requires providing credentials via --feed-credential parameter."
            echo "  --feed-credential <FEEDCREDENTIAL> Token to access Azure feed. Used as a query string to append to the Azure feed."
            echo "      -FeedCredential                This parameter typically is not specified."
            echo "  -i,--install-dir <DIR>             Install under specified location (see Install Location below)"
            echo "      -InstallDir"
            echo "  --architecture <ARCHITECTURE>      Architecture of dotnet binaries to be installed, Defaults to \`$architecture\`."
            echo "      --arch,-Architecture,-Arch"
            echo "          Possible values: x64, arm, arm64, s390x, ppc64le and loongarch64"
            echo "  --os <system>                    Specifies operating system to be used when selecting the installer."
            echo "          Overrides the OS determination approach used by the script. Supported values: osx, linux, linux-musl, freebsd, rhel.6."
            echo "          In case any other value is provided, the platform will be determined by the script based on machine configuration."
            echo "          Not supported for legacy links. Use --runtime-id to specify platform for legacy links."
            echo "          Refer to: https://aka.ms/dotnet-os-lifecycle for more information."
            echo "  --runtime <RUNTIME>                Installs a shared runtime only, without the SDK."
            echo "      -Runtime"
            echo "          Possible values:"
            echo "          - dotnet     - the Microsoft.NETCore.App shared runtime"
            echo "          - aspnetcore - the Microsoft.AspNetCore.App shared runtime"
            echo "  --dry-run,-DryRun                  Do not perform installation. Display download link."
            echo "  --no-path, -NoPath                 Do not set PATH for the current process."
            echo "  --verbose,-Verbose                 Display diagnostics information."
            echo "  --azure-feed,-AzureFeed            For internal use only."
            echo "                                     Allows using a different storage to download SDK archives from."
            echo "  --uncached-feed,-UncachedFeed      For internal use only."
            echo "                                     Allows using a different storage to download SDK archives from."
            echo "  --skip-non-versioned-files         Skips non-versioned files if they already exist, such as the dotnet executable."
            echo "      -SkipNonVersionedFiles"
            echo "  --jsonfile <JSONFILE>              Determines the SDK version from a user specified global.json file."
            echo "                                     Note: global.json must have a value for 'SDK:Version'"
            echo "  --keep-zip,-KeepZip                If set, downloaded file is kept."
            echo "  --zip-path, -ZipPath               If set, downloaded file is stored at the specified path."
            echo "  -?,--?,-h,--help,-Help             Shows this help message"
            echo ""
            echo "Install Location:"
            echo "  Location is chosen in following order:"
            echo "    - --install-dir option"
            echo "    - Environmental variable DOTNET_INSTALL_DIR"
            echo "    - $HOME/.dotnet"
            exit 0
            ;;
        *)
            say_err "Unknown argument \`$name\`"
            exit 1
            ;;
    esac

    shift
done

say_verbose "Note that the intended use of this script is for Continuous Integration (CI) scenarios, where:"
say_verbose "- The SDK needs to be installed without user interaction and without admin rights."
say_verbose "- The SDK installation doesn't need to persist across multiple CI runs."
say_verbose "To set up a development environment or to run apps, use installers rather than this script. Visit https://dotnet.microsoft.com/download to get the installer.\n"

if [ "$internal" = true ] && [ -z "$(echo $feed_credential)" ]; then
    message="Provide credentials via --feed-credential parameter."
    if [ "$dry_run" = true ]; then
        say_warning "$message"
    else
        say_err "$message"
        exit 1
    fi
fi

check_min_reqs
calculate_vars
# generate_regular_links call below will 'exit' if the determined version is already installed.
generate_download_links

if [[ "$dry_run" = true ]]; then
    print_dry_run
    exit 0
fi

install_dotnet

bin_path="$(get_absolute_path "$(combine_paths "$install_root" "$bin_folder_relative_path")")"
if [ "$no_path" = false ]; then
    say "Adding to current process PATH: \`$bin_path\`. Note: This change will be visible only when sourcing script."
    export PATH="$bin_path":"$PATH"
else
    say "Binaries of dotnet can be found in $bin_path"
fi

say "Note that the script does not resolve dependencies during installation."
say "To check the list of dependencies, go to https://learn.microsoft.com/dotnet/core/install, select your operating system and check the \"Dependencies\" section."
say "Installation finished successfully."
