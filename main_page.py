import streamlit as st


def main():
    st.set_page_config(layout="wide")
    st.markdown(
        """
        First create an initial backup file containing all the tags and image paths/URLs you want to annotate, 
        using the page `create initial backup` on the left side.  
        Then, once this initial backup file is created, select it in the page `annotate images` and start annotating.  
        Backup files are created automatically in the same folder as the initial backup file (with same format).  
        You can check or continue annotations by selecting the corresponding backup file in the page `annotate images`.
        """
    )

if __name__ == '__main__':
    main()
