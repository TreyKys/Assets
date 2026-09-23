using System.Runtime.CompilerServices;
using BVB.Toolkit.Interfaces;

namespace BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts;

public class FileInfoDto : IUploadFileContent
{
	[CompilerGenerated]
	private string a;

	[CompilerGenerated]
	private byte[] b;

	[CompilerGenerated]
	private string c;

	[CompilerGenerated]
	private long d;

	public string MimeType
	{
		[CompilerGenerated]
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = 15148;
			short num2 = num;
			num = 15148;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return a;
			}
		}
		[CompilerGenerated]
		set
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -7898;
			short num2 = num;
			num = -7898;
			switch (num2 == num)
			{
			}
			num = 0;
			if (num != 0)
			{
			}
			a = value;
		}
	}

	public byte[] Content
	{
		[CompilerGenerated]
		get
		{
			short num = 7863;
			short num2 = num;
			num = 7863;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return b;
			}
		}
		[CompilerGenerated]
		set
		{
			short num = -11764;
			short num2 = num;
			num = -11764;
			switch (num2 == num)
			{
			}
			num = 0;
			if (num != 0)
			{
			}
			num = 1;
			if (num != 0)
			{
			}
			b = value;
		}
	}

	public string FileName
	{
		[CompilerGenerated]
		get
		{
			short num = 775;
			short num2 = num;
			num = 775;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return c;
			}
		}
		[CompilerGenerated]
		set
		{
			short num = 25805;
			short num2 = num;
			num = 25805;
			switch (num2 == num)
			{
			}
			num = 1;
			if (num != 0)
			{
			}
			num = 0;
			if (num != 0)
			{
			}
			c = value;
		}
	}

	public long FileSize
	{
		[CompilerGenerated]
		get
		{
			short num = 12675;
			short num2 = num;
			num = 12675;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return d;
			}
		}
		[CompilerGenerated]
		set
		{
			short num = -2002;
			short num2 = num;
			num = -2002;
			switch (num2 == num)
			{
			}
			num = 0;
			if (num != 0)
			{
			}
			num = 1;
			if (num != 0)
			{
			}
			d = value;
		}
	}
}
