let 
  pkgs = import <nixos> {};
in pkgs.mkShell {
        buildInputs = with pkgs; [ 
          python3
          python3Packages.pip
          sqlite
          sqlite-utils
          rlwrap
  ];  
  shellHook = ''
        alias pip="PIP_PREFIX='$(pwd)/_build/pip_packages' \pip"
        alias sqlite3="rlwrap sqlite3"
        export PYTHONPATH="$(pwd)/_build/pip_packages/lib/python3.7/site-packages:$PYTHONPATH"
        unset SOURCE_DATE_EPOCH
  '';
}
