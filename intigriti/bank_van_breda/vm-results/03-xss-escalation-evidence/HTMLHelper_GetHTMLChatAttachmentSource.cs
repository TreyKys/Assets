	public static string GetHTMLChatAttachmentSource(AttachmentDto att)
	{
		short num = 0;
		int num2 = num;
		switch (num2)
		{
		default:
		{
			DateTime? attachmentAvailableUntil = default(DateTime?);
			string text = default(string);
			switch (0)
			{
			default:
				while (true)
				{
					string text2;
					switch (num2)
					{
					case 2:
						if (attachmentAvailableUntil.HasValue)
						{
							num = 5;
							num2 = num;
							continue;
						}
						goto case 3;
					case 4:
						text2 = "<span>" + string.Format(Messages.MessageAttachment.AttachmentAvailableUntil(), Helper.FormatDateTime(att.AttachmentAvailableUntil)) + "</span>";
						goto IL_021c;
					case 1:
						num = 0;
						num2 = num;
						continue;
					case 0:
					{
						num = -5300;
						short num3 = num;
						num = -5300;
						switch (num3 == num)
						{
						case false:
						case true:
							break;
						default:
							goto IL_018f;
						}
						break;
					}
					case 5:
						num = 6;
						num2 = num;
						continue;
					case 6:
						if (att.IsAttachmentAvailable)
						{
							num = 4;
							num2 = num;
						}
						else
						{
							num = 1;
							num2 = num;
						}
						continue;
					case 3:
						{
							return $"<a class=\"download-link\" href=\"javascript:invokeCSCode('att#{att.AttachmentID.ToString()}')\"><em><div class=\"icon download\"><!-- DL icon --></div></em><div>{att.FileName}</div>{text}</a>";
						}
						IL_021c:
						text = text2;
						num = 3;
						num2 = num;
						continue;
						IL_018f:
						num = 0;
						if (num != 0)
						{
						}
						text2 = "<span>" + Messages.MessageAttachment.AttachmentNotAvailable() + "</span>";
						goto IL_021c;
					}
					break;
				}
