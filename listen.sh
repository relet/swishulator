tshark -i wlp0s20f3 -l -w - udp | grep --color -aoE 'level["_][^,}]*,' 
#| grep -vE "[0-9]{2,},"
